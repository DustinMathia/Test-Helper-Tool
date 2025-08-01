import numpy as np
from scipy import stats
import plotly.graph_objects as go
import bisect
import math


def manipulate_data(data_list, column_names):
    manipulated_data = {}
    col_dtypes = data_list.dtype.fields
    numeric_cols = [
        col_name
        for col_name, col_type in col_dtypes.items()
        if col_type[0] in (np.int_, np.float64) and col_name != "reference_result"
    ]

    for col in numeric_cols:
        # Filter data based on reference_result
        if "reference_result" in data_list.dtype.names:
            positive_data_filtered = data_list[data_list["reference_result"] > 0][col]
            negative_data_filtered = data_list[data_list["reference_result"] < 0][col]
            unknown_data_filtered = data_list[data_list["reference_result"] == 0][col]
        else:
            unknown_data_filtered = data_list[col]
            positive_data_filtered = np.array([])
            negative_data_filtered = np.array([])

        all_data = np.concatenate(
            [positive_data_filtered, negative_data_filtered, unknown_data_filtered]
        )
        if all_data.size > 0:
            range_min = math.floor(all_data.min() - 1)
            range_max = math.ceil(all_data.max() + 1)
        else:
            range_min = 0
            range_max = 100  # Default range if no data

        range_value = [range_min, range_max]
        slider_value = range_min

        # Store data
        manipulated_data[col] = {
            "positive": {"data": np.sort(positive_data_filtered)},
            "negative": {"data": np.sort(negative_data_filtered)},
            "unknown": {"data": np.sort(unknown_data_filtered)},
            "range_min": range_min,
            "range_max": range_max,
            "range_value": range_value,
            "slider_value": slider_value,
        }
    return manipulated_data


def calculate_bin_edges(
    column_data, range_value, pos_chart_types, neg_chart_types, unknown_chart_types
):
    num_bins = 100
    bin_edges = np.linspace(range_value[0], range_value[1], num_bins + 1)
    return bin_edges


def fit_params(file_data):
    fitted_data = {}
    for column in file_data:
        positive_data = file_data[column]["positive"]["data"]
        negative_data = file_data[column]["negative"]["data"]
        unknown_data = file_data[column]["unknown"]["data"]

        # Initialize all parameters to None
        pnl, pns, pgc, pgl, pgs, pel, pes, penk, penl, pens = (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        nnl, nns, ngc, ngl, ngs, nel, nes, nenk, nenl, nens = (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        unl, uns, ugc, ugl, ugs, uel, ues, uenk, uenl, uens = (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        if positive_data.size > 0:
            pnl, pns = stats.norm.fit(positive_data)
            pgc, pgl, pgs = stats.gompertz.fit(positive_data)
            pel, pes = stats.expon.fit(positive_data)
            penk, penl, pens = stats.exponnorm.fit(positive_data)
        if negative_data.size > 0:
            nnl, nns = stats.norm.fit(negative_data)
            ngc, ngl, ngs = stats.gompertz.fit(negative_data)
            nel, nes = stats.expon.fit(negative_data)
            nenk, nenl, nens = stats.exponnorm.fit(negative_data)
        if unknown_data.size > 0:
            unl, uns = stats.norm.fit(unknown_data)
            ugc, ugl, ugs = stats.gompertz.fit(unknown_data)
            uel, ues = stats.expon.fit(unknown_data)
            uenk, uenl, uens = stats.exponnorm.fit(unknown_data)

        fitted_data[column] = {
            "positive": {
                "norm": {
                    "loc": pnl,
                    "scale": pns,
                },  #                'r-squared': None, 'aic': None, 'bic': None},
                "gompertz": {"c": pgc, "loc": pgl, "scale": pgs},
                "expon": {
                    "loc": pel,
                    "scale": pes,
                },  #                'r-squared': None, 'aic': None, 'bic': None},
                "exponnorm": {"K": penk, "loc": penl, "scale": pens},
            },  # 'r-squared': None, 'aic': None, 'bic': None}},
            "negative": {
                "norm": {
                    "loc": nnl,
                    "scale": nns,
                },  #                'r-squared': None, 'aic': None, 'bic': None},
                "gompertz": {"c": ngc, "loc": ngl, "scale": ngs},
                "expon": {
                    "loc": nel,
                    "scale": nes,
                },  #                'r-squared': None, 'aic': None, 'bic': None},
                "exponnorm": {"K": nenk, "loc": nenl, "scale": nens},
            },  # 'r-squared': None, 'aic': None, 'bic': None}},
            "unknown": {
                "norm": {
                    "loc": unl,
                    "scale": uns,
                },  #                'r-squared': None, 'aic': None, 'bic': None},
                "gompertz": {"c": ugc, "loc": ugl, "scale": ugs},
                "expon": {
                    "loc": uel,
                    "scale": ues,
                },  #                'r-squared': None, 'aic': None, 'bic': None},
                "exponnorm": {"K": uenk, "loc": uenl, "scale": uens},
            },  # , 'r-squared': None, 'aic': None, 'bic': None}}
        }
    return fitted_data


def make_roc_curve(
    positive_data, negative_data, unknown_data
):  # view confusion matrix chart @ https://en.wikipedia.org/wiki/Receiver_operating_characteristic
    total_positive = len(positive_data)
    total_negative = len(negative_data)
    total_unknown = len(unknown_data)

    if (
        total_positive == 0 and total_positive == 0
    ):  # usually if reference_result doesnt exist
        return {
            "population_data": [],
            "total_positive": 0,
            "total_negative": 0,
            "total_unknown": 0,
            "accumulated_positive_at_value": [],
            "accumulated_negative_at_value": [],
            "accumulated_unknown_at_value": [],
        }

    # make list of formated data values: tuple (value, True/False)
    positive_tuples = [(value, True) for value in positive_data]
    negative_tuples = [(value, False) for value in negative_data]
    unknown_tuples = [(value, None) for value in unknown_data]

    # create a sorted master list of all categories
    population_data = sorted(
        positive_tuples + negative_tuples + unknown_tuples, key=lambda x: x[0]
    )

    current_positive_count = 0
    current_negative_count = 0
    current_unknown_count = 0

    accumulated_positive_at_value = []
    accumulated_negative_at_value = []
    accumulated_unknown_at_value = []

    for value, label in population_data:
        if label is True:
            current_positive_count += 1
        elif label is False:
            current_negative_count += 1
        elif label is None:
            current_unknown_count += 1

        accumulated_positive_at_value.append(current_positive_count)
        accumulated_negative_at_value.append(current_negative_count)
        accumulated_unknown_at_value.append(current_unknown_count)

    return {
        "population_data": population_data,
        "total_positive": total_positive,
        "total_negative": total_negative,
        "total_unknown": total_unknown,
        "accumulated_positive_at_value": accumulated_positive_at_value,
        "accumulated_negative_at_value": accumulated_negative_at_value,
        "accumulated_unknown_at_value": accumulated_unknown_at_value,
    }


def plot_roc_curve(roc_data, threshold_index):
    population_data = roc_data["population_data"]
    total_positive = roc_data["total_positive"]
    total_negative = roc_data["total_negative"]
    acc_pos = roc_data["accumulated_positive_at_value"]
    acc_neg = roc_data["accumulated_negative_at_value"]

    TPR_plot = [1]
    FPR_plot = [1]
    if total_positive == 0 and total_negative == 0:
        return go.Figure()

    for k in range(len(population_data)):
        positives_less_than_current_value = acc_pos[k - 1] if k > 0 else 0
        negatives_less_than_current_value = acc_neg[k - 1] if k > 0 else 0

        tp_at_k = total_positive - positives_less_than_current_value
        fp_at_k = total_negative - negatives_less_than_current_value

        tpr_at_k = tp_at_k / total_positive if total_positive > 0 else 0
        fpr_at_k = fp_at_k / total_negative if total_negative > 0 else 0

        TPR_plot.append(tpr_at_k)
        FPR_plot.append(fpr_at_k)
    TPR_plot.append(0)
    FPR_plot.append(0)

    thresh_pt_x = 0
    thresh_pt_y = 0

    if total_positive == 0 and total_negative == 0:
        pass
    elif threshold_index == len(population_data):
        thresh_pt_x = 0
        thresh_pt_y = 0
    elif threshold_index == 0:
        thresh_pt_x = 1
        thresh_pt_y = 1
    else:
        thresh_pt_x = FPR_plot[threshold_index + 1]
        thresh_pt_y = TPR_plot[threshold_index + 1]

    fig = go.Figure()
    if FPR_plot and TPR_plot:  # Ensure lists are not empty
        fig.add_trace(
            go.Scatter(
                x=FPR_plot, y=TPR_plot, mode="lines", line_shape="hv", name="ROC Curve"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[thresh_pt_x],
                y=[thresh_pt_y],
                mode="markers",
                marker=dict(color="orange", size=10, symbol="circle"),
                name="Threshold Point",
            )
        )
        fig.update_layout(
            xaxis_title="False Positive Rate (FPR)",
            yaxis_title="True Positive Rate (TPR)",
            xaxis=dict(range=[0, 1]),
            yaxis=dict(range=[0, 1]),
            # hovermode="x unified" # Improves hover experience
        )
    return fig


def bisect_population_w_threshold(roc_data, threshold_value):
    population_data_values = [item[0] for item in roc_data["population_data"]]
    # bisect_left returns an insertion point `i` such that all `a[k]` for `k < i` have `a[k] < x`.
    # And all `a[k]` for `k >= i` have `a[k] >= x`.
    # This `i` directly tells us how many elements are strictly less than `threshold_value`.
    index = bisect.bisect_left(population_data_values, threshold_value)
    return index


def gen_roc_table(roc_data, threshold_value, norm_params):
    roc_table_header = ["TP", "FN", "FP", "TN"]
    if not roc_data or not roc_data.get("population_data"):
        # Return an empty figure or a figure with a message if data is not available
        return (
            [
                [None, None, None, None],
                [None, None, None, None],
                [None, None, None, None],
            ],
            roc_table_header,
            0,
        )

    i = bisect_population_w_threshold(roc_data, threshold_value)
    num_data_points = len(roc_data["population_data"])

    # Determine counts of samples *below* the threshold (classified as Negative)
    # If i is 0, no points are below the threshold.
    # Otherwise, accumulated_positive[i-1] gives the count of positives up to population_data[i-1].
    if i == 0:
        fn_val = 0
        tn_val = 0
        un_val = 0
    else:
        fn_val = roc_data["accumulated_positive_at_value"][i - 1]
        tn_val = roc_data["accumulated_negative_at_value"][i - 1]
        un_val = roc_data["accumulated_unknown_at_value"][i - 1]

    # Determine counts of samples *at or above* the threshold (classified as Positive)
    tp_val = (
        (roc_data["total_positive"] - fn_val)
        if roc_data["total_positive"] is not None
        else 0
    )
    fp_val = (
        (roc_data["total_negative"] - tn_val)
        if roc_data["total_negative"] is not None
        else 0
    )
    up_val = (
        (roc_data["total_unknown"] - un_val)
        if roc_data["total_unknown"] is not None
        else 0
    )

    tpr_val = (
        round(tp_val / roc_data["total_positive"], 2)
        if roc_data["total_positive"] > 0
        else 0
    )
    fpr_val = (
        round(fp_val / roc_data["total_negative"], 2)
        if roc_data["total_negative"] > 0
        else 0
    )
    tnr_val = (
        round(tn_val / roc_data["total_negative"], 2)
        if roc_data["total_negative"] > 0
        else 0
    )  # Specificity
    fnr_val = (
        round(fn_val / roc_data["total_positive"], 2)
        if roc_data["total_positive"] > 0
        else 0
    )  # Miss Rate

    total_classified = (roc_data["total_positive"] or 0) + (
        roc_data["total_negative"] or 0
    )
    acc_val = (
        round((tp_val + tn_val) / total_classified, 2) if total_classified > 0 else 0
    )

    # tp_val = roc_data['TP'][i] if roc_data['TP'] else None
    # fp_val = roc_data['FP'][i] if roc_data['FP'] else None
    # tn_val = roc_data['TN'][i] if roc_data['TN'] else None
    # fn_val = roc_data['FN'][i] if roc_data['FN'] else None
    # up_val = roc_data['UP'][i] if roc_data['UP'] else None
    # un_val = roc_data['UN'][i] if roc_data['UN'] else None
    # tpr_val = round(roc_data['TPR'][i], 2) if roc_data['TPR'] and roc_data['TPR'][i] is not None else None
    # fpr_val = round(roc_data['FPR'][i], 2) if roc_data['FPR'] and roc_data['FPR'][i] is not None else None
    # tnr_val = round(roc_data['TNR'][i], 2) if roc_data['TNR'] and roc_data['TNR'][i] is not None else None
    # fnr_val = round(roc_data['FNR'][i], 2) if roc_data['FNR'] and roc_data['FNR'][i] is not None else None
    # acc_val = round(roc_data['ACC'][i], 2) if roc_data['ACC'] and roc_data['ACC'][i] is not None else None

    mean = norm_params["loc"]
    std = norm_params["scale"]
    z_score = (threshold_value - mean) / std if std != 0 else float("nan")
    z_score = round(z_score, 2)

    roc_table_header = ["TP", "FN", "FP", "TN"]
    roc_table = [
        [tp_val, "Sensitivity (TPR)", tpr_val, "Unkn. as Pos.", up_val],
        [fn_val, "Miss Rate (FNR)", fnr_val, "Unkn. as Neg.", un_val],
        [fp_val, "False Alarm (FPR)", fpr_val, "Accuracy", acc_val],
        [tn_val, "Specificity (TNR)", tnr_val, "Z-score", z_score],
    ]
    return roc_table, roc_table_header, i

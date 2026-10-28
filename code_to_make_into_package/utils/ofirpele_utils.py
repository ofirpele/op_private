ACROBAT_READER_EXE_NAME = "AcroRd32.exe"
OUTPUT_FOLDER = ""

import enum
import json
import os
import pickle
import subprocess  # opening the pdf
import sys
from dataclasses import dataclass

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import psutil
except:
    pass
try:
    import functools
except:
    pass
try:
    import bisect
except:
    pass
try:
    import unittest
except:
    pass
try:
    import cloudpickle
except:
    pass

try:
    import smtplib
    from email import encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.utils import formatdate
    from pathlib import Path
except:
    pass


#################################################################
def min_len_format(num, formats=[lambda num: f"{num:.2e}", lambda num: f"{num}"]):
    min_str = formats[0](num)
    for f in formats:
        new_str = f(num)
        if len(new_str) < len(min_str):
            min_str = f(num)
    return min_str


def num_format(num, latex_format=True, precision=3, abs_num_e_limit=1e4):
    res = "{n:.{p}{c}}".format(n=num, p=precision, c="e" if abs(num) > abs_num_e_limit else "g")
    # print(res, end='\t')

    g_res_arr = res.split("e")
    if len(g_res_arr) == 2:
        # remove exponent plus sign and leading zeros
        num_b_str = g_res_arr[1].lstrip("+").lstrip("0")
        # remove exponent leading zeros when it is negative
        if num_b_str[0] == "-":
            num_b_str = f"-{num_b_str[1:].lstrip('0')}"

        num_a_str = g_res_arr[0]
        # if there is a decimal point
        #  remove trailing zeros after the decimal point,
        if "." in num_a_str:
            num_a_str = num_a_str.rstrip("0").rstrip(".")

        l_symbol = "\\times" if latex_format else "x"

        # change 1x10^num_b or -1x10^num_b to
        #          10^num_b or   -10^num_b
        if num_a_str == "-1" or num_a_str == "1":
            l_symbol = ""
            if num_a_str == "-1":
                l_symbol = "-"
            num_a_str = ""

        res_begin = f"{num_a_str}{l_symbol}10^"
        if latex_format:
            res = f"${res_begin}{{{num_b_str}}}$"
        else:
            res = f"{res_begin}{num_b_str}"

    if res == "-0":
        res = "0"

    return res


class test_num_format(unittest.TestCase):
    def test_a(self):
        self.assertEqual(
            "-10^-7", num_format(-1e-07, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "10^-7", num_format(1e-07, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "-0.001", num_format(-0.001, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "0.001", num_format(0.001, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "0.346", num_format(0.3456, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "1.32", num_format(1.3221, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "50.3", num_format(50.343, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "0", num_format(-0.0, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "10^9", num_format(1000000032, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "-10^9", num_format(-1000000032, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "1.043x10^9",
            num_format(1043234532, latex_format=False, precision=3, abs_num_e_limit=1e4),
        )
        self.assertEqual(
            "-inf", num_format(-np.inf, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "inf", num_format(np.inf, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )
        self.assertEqual(
            "nan", num_format(np.nan, latex_format=False, precision=3, abs_num_e_limit=1e4)
        )


#################################################################


#################################################################
class unbuffered_stream:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


def redirect_stdout_stderr(filename_prefix=""):
    def create_stream(name):
        filename_no_location = f"{filename_prefix}{name}"
        filename_no_location += ".txt"
        filename = f"{OUTPUT_FOLDER}{filename_no_location}"
        return unbuffered_stream(open(filename, "w")), filename_no_location

    sys.stdout, stdout_filename_no_location = create_stream("_stdout")
    sys.stderr, stderr_filename_no_location = create_stream("_stderr")


def redirect_stdout_stderr_by_REDIRECT_OUTPUT_enviorment(filename_prefix=""):
    if os.environ.get("REDIRECT_OUTPUT") == "true":
        redirect_stdout_stderr(filename_prefix)

        with open(f"{OUTPUT_FOLDER}stdout_stderr_local_filenames.txt", "w") as file:
            file.write(f"{OUTPUT_FOLDER}{stdout_filename_no_location}\n")
            file.write(f"{OUTPUT_FOLDER}{stderr_filename_no_location}\n")


#################################################################


#################################################################
def send_me_email(subject="", message="", files=[]):
    """Compose and send email with provided info and attachments.

    Args:
        subject (str): message title
        message (str): message body
        files (list[str] or single str): list of file paths or one file path to be attached to email

    """

    if isinstance(files, str):
        files = [files]

    msg = MIMEMultipart()
    msg["From"] = MY_EMAIL
    msg["To"] = MY_EMAIL
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject

    msg.attach(MIMEText(message))

    for path in files:
        part = MIMEBase("application", "octet-stream")
        with open(path, "rb") as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{Path(path).name}"')
        msg.attach(part)

    smtp = smtplib.SMTP("localhost")
    smtp.sendmail(MY_EMAIL, MY_EMAIL, msg.as_string())
    smtp.quit()


def send_me_email_files(files=[]):
    subject = " ".join(files)
    if isinstance(files, str):
        subject = files
    send_me_email(subject=subject, files=files)


#################################################################


#################################################################
def ranges_range(arr, pair_condition):
    if len(arr) == 0:
        return
    rb = arr[0]
    re = arr[0]
    for i in range(1, len(arr)):
        if pair_condition(arr[i - 1], arr[i]):
            re = arr[i]
        else:
            yield rb, re
            rb = arr[i]
            re = arr[i]
    yield rb, re


# Example Usage:
#   ranges_range_visualization([3,4,5, 1,2, 2], lambda x,y : y-x==1)
#   == [ 3->5 1->2 2 ]
def ranges_range_visualization(arr, pair_condition):
    def print_n(p):
        print(p, end=" ")

    print_n("[")
    for rb, re in ranges_range(arr, pair_condition):
        if rb == re:
            print_n(rb)
        else:
            print_n(f"{rb}->{re}")
    print("]")


#################################################################


#################################################################
from time import time

_tstart_stack = []


def tic():
    print("============================== Begin measuring time ==============================")
    _tstart_stack.append(time())


def toc():
    print(f"============================== Elasped time: {time() - _tstart_stack.pop()} ======")


#################################################################


#################################################################
def print_signature(func):
    @functools.wraps(func)
    def wrapper_print_signature(*args, **kwargs):
        args_repr = [repr(a) for a in args]  # 1
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
        signature = ", ".join(args_repr + kwargs_repr)  # 3
        print(f"-------------->    Calling {func.__name__}({signature})")
        value = func(*args, **kwargs)
        print(f"-------------->    {func.__name__!r} returned {value!r}")  # 4
        return value

    return wrapper_print_signature


#################################################################


#################################################################
# usage (change on to True to get normal behavior):
#   on_off_Counter = on_off_Counter(Counter, on = False)
#   c = off_on_Counter()
def on_off_class(Cls, on, get_set_item_return_when_off=0, len_when_off=0):
    class NewCls:
        def __init__(self, *args, **kwargs):
            self.on = on
            self.oInstance = Cls(*args, **kwargs)

        def __reduce__(self):
            return self.oInstance.__reduce__()

        def __repr__(self):
            if on:
                return self.oInstance.__repr__()
            return ""

        def __len__(self):
            if on:
                return self.oInstance.__len__()
            return len_when_off

        def __setitem__(self, key, value):
            if on:
                return self.oInstance.__setitem__(key, value)
            return get_set_item_return_when_off

        def __getitem__(self, key):
            if on:
                return self.oInstance.__getitem__(key)
            return get_set_item_return_when_off

        def __getattribute__(self, s):
            class do_nothing_functor:
                def __init__(self):
                    pass

                def __repr__(self):
                    return ""

                def __call__(self, *args, **kargs):
                    pass

            if on:
                try:
                    x = super(NewCls, self).__getattribute__(s)
                except AttributeError:
                    return self.oInstance.__getattribute__(s)
                else:
                    return x
            else:
                return do_nothing_functor()

    return NewCls


#################################################################


#################################################################
def df_query_to_nparray(df, query_dict, data_name="Value"):
    idx_query_true = np.full(df.shape[0], True)
    for key, value in query_dict.items():
        idx_query_true = np.logical_and(idx_query_true, np.array(df[key]) == value)
    query_value = np.array(df.loc[idx_query_true, data_name]).astype(float)
    return query_value


#################################################################


#################################################################
def replace_problematic_signs_in_a_filename(filename, colonOk=False):
    if not colonOk:
        filename = filename.replace(":", "_")
    filename = filename.replace(" ", "_")
    filename = filename.replace("(", "_")
    filename = filename.replace(")", "_")
    filename = filename.replace("\n", "_")
    filename = filename.replace("#", "num_")
    filename = filename.replace("*", "_mult_")
    filename = filename.replace("=", "_eq_")
    filename = filename.replace("<", "_smaller_")
    filename = filename.replace(">", "_bigger_")
    filename = filename.replace("&", "_and_")
    return filename


#################################################################


#################################################################
def kill_process(PROCESS_EXE_NAME: str):
    for p in psutil.process_iter():
        if p.name() == PROCESS_EXE_NAME:
            p.terminate()


#################################################################


#################################################################
_pdf_save_and_show_first_call = True


def pdf_save_and_show(
    fig_handle, pdf_filename, show=True, title_active=True, title_addition="", colonOk=False
):
    if title_active:
        plt.title(f"{pdf_filename} {title_addition}")

    pdf_filename = f"{OUTPUT_FOLDER}{pdf_filename}"

    # Closes acrobat reader
    global _pdf_save_and_show_first_call
    if _pdf_save_and_show_first_call and show:
        _pdf_save_and_show_first_call = False
        try:
            kill_process(ACROBAT_READER_EXE_NAME)
        except Exception:
            pass

    pdf_filename = replace_problematic_signs_in_a_filename(pdf_filename, colonOk)
    pdf_filename += ".pdf"
    # fig_handle.tight_layout()
    fig_handle.savefig(pdf_filename, bbox_inches="tight")
    if show:
        subprocess.Popen(pdf_filename, shell=True)
    return pdf_filename


def pdf_png_save_and_show(
    fig_handle,
    pdf_png_filename,
    show=True,
    title_active=True,
    title_addition="",
    png_dpi=1000,
    colonOk=False,
):
    pdf_png_filename = pdf_save_and_show(
        fig_handle, pdf_png_filename, show, title_active, title_addition, colonOk
    )
    fig_handle.savefig(f"{pdf_png_filename}.png", format="png", dpi=png_dpi)


# func([x1,x2]) should be legal where x1, x2 are elements of the range
def pdf_png_save_and_show_and_return_2d_func(
    x1_min, x1_max, x2_min, x2_max, vis_jump, percentage_nans, func, title_str
):
    x1_range = np.arange(x1_min, x1_max, vis_jump)
    x2_range = np.arange(x2_min, x2_max, vis_jump)
    y_all = np.empty((len(x2_range), len(x1_range)))
    found_nans = False
    nans_all = np.zeros((len(x2_range), len(x1_range)))
    for x1i, x1_t in enumerate(x1_range):
        for x2i, x2_t in enumerate(x2_range):
            x1 = x1_t
            if percentage_nans > np.random.uniform():
                x1 = np.nan
                found_nans = True
                nans_all[x2i, x1i] = 1
            x2 = x2_t
            if percentage_nans > np.random.uniform():
                x2 = np.nan
                found_nans = True
                nans_all[x2i, x1i] = 1
            y_all[x2i, x1i] = func([x1, x2])

    num_subplots = 2 if found_nans else 1
    f_h, axs = plt.subplots(1, num_subplots, squeeze=False, constrained_layout=True)
    f_h.suptitle(title_str)
    im_h = axs[0, 0].imshow(
        y_all,
        extent=[x1_min, x1_max, x2_min, x2_max],
        cmap="jet",
        interpolation="nearest",
        origin="lower",
        aspect="auto",
    )
    formatter_wrapper().colorbar(
        im_h, ax=axs[0, 0], ticks=np.linspace(np.amin(y_all), np.amax(y_all), num=10)
    )
    axs[0, 0].set(xlabel="x1", ylabel="x2")
    if found_nans:
        im_h = axs[0, 1].imshow(
            nans_all,
            extent=[x1_min, x1_max, x2_min, x2_max],
            cmap=plt.cm.get_cmap("Blues", 2),
            interpolation="nearest",
            origin="lower",
            aspect="auto",
        )
        formatter_wrapper().colorbar(im_h, ax=axs[0, 1], ticks=[0, 1])
        axs[0, 1].set(xlabel="x1", ylabel="x2")
        axs[0, 1].set_title("x1 or x2 is nan")

    pdf_png_save_and_show(f_h, title_str, show=True, title_active=False)
    return y_all


# _pdf_save_and_show_pids = []
# import psutil
# def kill_pid_if_exists(pid):
#    try:
#        if psutil.pid_exists(pid):
#            psutil.Process(pid).kill()
#    except:
#        pass
# def pdf_save_and_show_close_all_pdfs():
#    for pid in _pdf_save_and_show_pids:
#        print(pid)
#        for child in parent.children(recursive=True):
#            kill_pid_if_exists(child.pid)
#        kill_pid_if_exists(pid)


# returns axes_full and then an array of axes cols major:
# [axes_full, axes_x0_y0, axes_x0_y1, ...]
def create_subplots(fig_handle, rows_num, cols_num, tight_layout=True, subplots_hspace=0.6):
    if tight_layout:
        fig_handle.tight_layout()
    fig_handle.subplots_adjust(hspace=subplots_hspace)
    ax = fig_handle.add_subplot(111)
    # Turn off axis lines and ticks of the big subplot
    ax.spines["top"].set_color("none")
    ax.spines["bottom"].set_color("none")
    ax.spines["left"].set_color("none")
    ax.spines["right"].set_color("none")
    ax.tick_params(labelcolor="w", top=False, bottom=False, left=False, right=False)
    axes = [ax]
    s_i = 1
    for r in range(rows_num):
        for c in range(cols_num):
            axes.append(fig_handle.add_subplot(rows_num, cols_num, s_i))
            s_i += 1

    return axes


@dataclass
class formatter_wrapper:
    formatter: ... = matplotlib.ticker.FormatStrFormatter("%.1f")

    def colorbar(self, *args, **kwargs):
        cbar = plt.colorbar(*args, **kwargs)
        cbar.ax.yaxis.set_major_formatter(self.formatter)


# x - see plt.hist
def hist_plot(
    x,
    hist_params={},
    grid_params={"color": "white"},
    xticks_num_format=num_format,
    xticks_params={"fontsize": 5},
    count_numbers_text_add_to_y_location=0.01,
    count_numbers_text_params={"ha": "center", "fontsize": 7},
):
    """
    Compute and plot a histogram like plt.hist,
    but only works with a single array
    and better for a small number of bins
    Other differences between this and plt.hist:
     - bins are clearly separated
     - count numbers are on the top of the bars (unless 0)
     - the min and max values of each bin with more than one count
       is shown below the bin, if min==max only one value is shown
     - less clutter (white grid by default, no y axis numbers, no top & right spines)

    :param array x: input values
    :param dict hist_params: params passed to plt.hist
    :param dict grid_params: params passed to plt.grid
    :param callable xticks_num_format: function that transforms the min&max values below the bin to a string
    :param dict xticks_params: params passed to plt.xticks
    :param float count_numbers_text_add_to_y_location: how much to add to the y location above the bars for the count numbers
    :params dict count_numbers_text_params: params passed to plt.text for the count numbers
    :return: see plt.hist

    """

    hist_counts, bins, patches = plt.hist(x, **hist_params)

    # grid
    minor_locator = matplotlib.ticker.AutoMinorLocator(2)
    plt.gca().xaxis.set_minor_locator(minor_locator)
    plt.grid(which="minor", **grid_params)

    # ticks & labels
    xticks = [(bins[idx + 1] + value) / 2 for idx, value in enumerate(bins[:-1])]
    b_i = 0
    min_of_bin = np.full((len(bins) - 1,), np.inf)
    max_of_bin = np.full((len(bins) - 1,), -np.inf)
    for v in np.sort(x):
        while b_i < len(bins) - 2 and v >= bins[b_i + 1]:
            b_i += 1
        min_of_bin[b_i] = min(v, min_of_bin[b_i])
        max_of_bin[b_i] = max(v, max_of_bin[b_i])
    xticks_labels = []
    for minv, maxv in zip(min_of_bin, max_of_bin):
        assert not (bool(minv == np.inf) ^ bool(maxv == -np.inf))
        if minv == np.inf:
            xticks_labels.append("")
        else:
            minv_str = xticks_num_format(minv)
            maxv_str = xticks_num_format(maxv)
            if minv == maxv:
                xticks_labels.append(minv_str)
            else:
                xticks_labels.append(f"{minv_str}\nto\n{maxv_str}")

    plt.xticks(xticks, labels=xticks_labels, **xticks_params)
    # remove major and minor ticks from the x axis, but keep the labels
    # plt.gca().tick_params(axis='x', which='both', length=0)
    # remove y ticks
    plt.yticks([])

    # Hide spines
    plt.gca().spines["right"].set_visible(False)
    plt.gca().spines["top"].set_visible(False)

    # text above bars
    for idx, value in enumerate(hist_counts):
        if value > 0:
            plt.text(
                xticks[idx],
                value + count_numbers_text_add_to_y_location,
                int(value),
                **count_numbers_text_params,
            )

    return hist_counts, bins, patches


# nparrs: list of all nparrs to plot as bars
# offsets: x offset of this bar (should be small enough)
# labels: label of each nparr
# ticks: np.array of the ticks (note, this is not exactly bins, one bin of ticks[-1]+np.finfo(float).eps is added
#                               also, should include min and max of nparrs)
#        If ticks is None (default) then it is equal to all unique values in nparrs
# width: the width of each bar
#
# Example:
# fig_handle = plt.figure()
# o.hist_mult_bar( (np.random.normal(loc = 0.0, scale = 1.0, size = (1000,)),
#                  np.random.normal(loc = 5.0, scale = 3.0, size = (1000,))),
#                  (-0.15,
#                  0.15),
#                  ('gaussian 1',
#                  'gaussian 2')
#                )
# plt.xlabel('value')
# plt.ylabel('#elements')
# plt.legend(loc="upper right")
# o.pdf_save_and_show(fig_handle, 'random gaussians')
def hist_mult_bar(
    nparrs,
    offsets,
    labels=None,
    ticks=None,
    width=4,
    textabovebarsfontsize=None,
    xticksrotation="vertical",
    colors=["r", "c"],
):
    # if offsets is None:
    #    offsets =

    if ticks is None:
        ticks = np.unique(np.concatenate(nparrs))

    assert len(nparrs) == len(offsets)
    if len(nparrs) == 1:
        assert labels is None
    else:
        assert len(nparrs) == len(labels)

    bins = np.append(ticks, ticks[-1] + np.finfo(float).eps)

    for i in range(len(nparrs)):
        assert bins[0] <= np.min(nparrs[i]), f"    {bins[0]}  > {np.min(nparrs[i])}"
        assert bins[-1] >= np.max(nparrs[i]), f"    {bins[-1]} < {np.max(nparrs[i])}"
        hist = np.histogram(nparrs[i], bins=bins)
        if labels is None:
            curr_label = None
        else:
            curr_label = labels[i]
        plt.bar(hist[1][:-1] + offsets[i], hist[0], width, label=curr_label, color=colors[i])
        if textabovebarsfontsize:
            for e in range(len(hist[0])):
                if hist[0][e] != 0:
                    plt.text(
                        hist[1][e] + offsets[i],
                        hist[0][e],
                        str(hist[0][e]),
                        va="center",
                        ha="center",
                        fontsize=textabovebarsfontsize,
                        bbox=dict(lw=0, facecolor=colors[i], alpha=0.5, pad=0),
                        fontweight="bold",
                    )

    plt.xticks(ticks, rotation=xticksrotation)
    plt.xlim(ticks[0] - width * 2, ticks[-1] + width * 2)


#################################################################


#################################################################
# Returns None if obj is not in namespace/locals
def first_name_of_variable_in_namespace_str(obj, namespace):
    names = [name for name in namespace if namespace[name] is obj]
    if not names:
        return None
    return names[0]


def first_name_of_variable_in_locals_str(obj):
    import inspect

    frame = inspect.currentframe()
    try:
        return first_name_of_variable_in_namespace_str(obj, frame.f_back.f_locals)
    finally:
        del frame


def first_name_of_variable_in_father_locals_str(obj):
    import inspect

    frame = inspect.currentframe()
    try:
        return first_name_of_variable_in_namespace_str(obj, frame.f_back.f_back.f_locals)
    finally:
        del frame


#################################################################


#################################################################
def np_savetxt(filename, nparr):
    np.savetxt(os.path.normcase(f"{OUTPUT_FOLDER}{filename}.txt"), nparr)


def np_save(filename, nparr):
    np.save(os.path.normcase(f"{OUTPUT_FOLDER}{filename}.npbin"), nparr)


def savetxt_filename_is_varname(nparr):
    np_savetxt(first_name_of_variable_in_father_locals_str(nparr), nparr)


def save_filename_is_varname(nparr):
    np_save(first_name_of_variable_in_father_locals_str(nparr), nparr)


def savetxt_and_save_filename_is_varname(nparr):
    np_savetxt(first_name_of_variable_in_father_locals_str(nparr), nparr)
    np_save(first_name_of_variable_in_father_locals_str(nparr), nparr)


#################################################################


#################################################################
def ecdf(a):
    x, counts = np.unique(a, return_counts=True)
    cusum = np.cumsum(counts)
    return x, cusum / cusum[-1]


def moving_average(x, w):
    return np.convolve(x, np.ones(w), "valid") / w


#################################################################


#################################################################
def create_dir(path, print_new_path=True):
    if not os.path.exists(path):
        os.makedirs(path)
        if print_new_path:
            print(f"{path} created")


#################################################################


#################################################################
def save_json(data, jfile_name, override=True):
    open_mode = "w" if override else "x"
    with open(jfile_name, open_mode) as fp:
        json.dump(data, fp)


def load_json(jfile_name):
    with open(jfile_name) as json_file:
        data = json.load(json_file)
    return data


#################################################################


#################################################################
def write_pickle_obj(filename, obj, use_cloudpickle=False, override=True):
    open_mode = "wb+" if override else "xb+"
    filename = os.path.normcase(f"{OUTPUT_FOLDER}{filename}.pkl")
    with open(filename, open_mode) as fp:
        if use_cloudpickle:
            cloudpickle.dump(obj, fp, pickle.HIGHEST_PROTOCOL)
        else:
            pickle.dump(obj, fp, pickle.HIGHEST_PROTOCOL)


def read_pickle_obj(filename, use_cloudpickle=False):
    filename = os.path.normcase(filename + ".pkl")
    with open(filename, "rb") as fp:
        if use_cloudpickle:
            obj = cloudpickle.load(fp)
        else:
            obj = pickle.load(fp)
    return obj


#################################################################


#################################################################
def dprint(obj):
    s = first_name_of_variable_in_father_locals_str(obj)
    print(f"{s}={obj}")


#################################################################


#################################################################
def is_convertible_to_type(element, type):
    try:
        type(element)
        return True
    except ValueError:
        return False


def is_convertible_to_float(element):
    return is_convertible_to_type(element, float)


#################################################################


#################################################################
def assert_not_any_is_nan(nparr, pre_err_msg="", post_err_msg=""):
    if np.isnan(nparr).any():
        print(
            f"{pre_err_msg} {first_name_of_variable_in_father_locals_str(nparr)} has at least one nan in it {post_err_msg}:"
        )
        print(nparr)
        print()
        sys.exit(1)


def assert_all_is_finite(nparr, pre_err_msg="", post_err_msg=""):
    if not np.isfinite(nparr).all():
        print(
            f"{pre_err_msg} {first_name_of_variable_in_father_locals_str(nparr)} is not all finite {post_err_msg}:"
        )
        print(nparr)
        print()
        sys.exit(1)


def assert_all_is_not_zero(nparr, pre_err_msg="", post_err_msg=""):
    if (nparr == 0).any():
        print(
            f"{pre_err_msg} {first_name_of_variable_in_father_locals_str(nparr)} is not all different from zero {post_err_msg}:"
        )
        print(nparr)
        print()
        sys.exit(1)


def assert_equal(a, b, msg):
    unittest.TestCase().assertEqual(a, b, msg)


#################################################################


#################################################################
def function_count_calls(func):
    @functools.wraps(func)
    def decor(*args, **kwargs):
        decor.count += 1
        return func(*args, **kwargs)

    decor.count = 0
    return decor


#################################################################

#################################################################
# class image_coordinate_string:
#    def __init__(self, im):
#        self.im = im
#    def __call__(self, x, y):
#        x = int(x)
#        y = int(y)
#        rep_str = f'x={x}, y={y}'
#        if self.im.shape[2]==1:
#            rep_str += ', gray={self.im[y,x]}'
#        elif self.im.shape[2]==3:
#            rep_str += f', R={self.im[y,x,2]}, G={self.im[y,x,1]}, B={self.im[y,x,0]}'
#        else:
#            rep_str += f' INFO={im[y,x]}'
#        print(rep_str)
#        return rep_str
# fig, ax = plt.subplots()
# im = ax.imshow(image, interpolation='none')
# ax.format_coord = image_coordinate_string(image)

# @function_count_calls
# def imshow(image, window_name = None):
#    if window_name is None:
#        window_name = f'Image Window #{imshow.count}'
#    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
#    cv2.imshow(window_name, image)
#    plt.show()
#    cv2.waitKey()
#    #cv2.destroyAllWindows()
#    # add mouse hover like in here but not event of click:
#    #https://www.pyimagesearch.com/2015/03/09/capturing-mouse-click-events-with-python-and-opencv/


def bounding_box_of_color(im, color):
    min_r_color = im.shape[0]
    max_r_color = -1
    min_c_color = im.shape[1]
    max_c_color = -1
    for r in range(im.shape[0]):
        for c in range(im.shape[1]):
            if (im[r, c, :] == color).all():
                min_r_color = min(min_r_color, r)
                max_r_color = max(max_r_color, r)
                min_c_color = min(min_c_color, c)
                max_c_color = max(max_c_color, c)
    return (min_c_color, min_r_color), (max_c_color, max_r_color)


#################################################################


#################################################################
def str_from_files(*filenames):
    filenames_str = ""
    for filename in filenames:
        with open(filename) as myfile:
            filenames_str += myfile.read()
    return filenames_str


#################################################################


#################################################################
def change_data_aspect_ratio_of_plot(ax, ratio=1.0):
    xleft, xright = ax.get_xlim()
    ybottom, ytop = ax.get_ylim()
    ax.set_aspect(abs((xright - xleft) / (ybottom - ytop)) * ratio)


#################################################################


#################################################################
class bin_arr:
    def __init__(self, num_total_bits, num_one_bits):
        assert num_one_bits <= num_total_bits
        self.arr = np.zeros(num_total_bits, dtype=bool)
        self.arr[:num_one_bits] = 1
        np.random.shuffle(self.arr)

    def flip_bits(self, num_bits):
        inds_to_flip = np.random.choice(self.arr.shape[0], num_bits, replace=False)
        self.arr[inds_to_flip] = ~self.arr[inds_to_flip]

    def flip_bit(self, key):
        self.arr[key] = ~self.arr[key]

    def num_diff_bits(self, other):
        return (self.arr != other.arr).sum()

    def __getitem__(self, key):
        return self.arr[key]

    def __setitem__(self, key, val):
        self.arr[key] = val

    def __len__(self):
        return self.arr.shape[0]

    def __str__(self):
        str = "[ "
        for x in self.arr:
            if x:
                str += "1 "
            else:
                str += "0 "
        return str + "]"

    def __eq__(self, other):
        return (self.arr == other.arr).all()


#################################################################


#################################################################
def find_lb_ub_in_sorted_arr(val, arr, cyclic=False, cyclic_max_val=None):
    assert all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))
    assert len(arr) >= 2
    assert arr[0] <= val
    if cyclic:
        assert val <= cyclic_max_val
        assert arr[-1] < cyclic_max_val
        if val > arr[-1]:
            return (len(arr) - 1, 0)
    else:
        assert val <= arr[-1]

    ub_i = bisect.bisect_left(arr, val)
    lb_i = max(0, ub_i - 1)

    assert lb_i + 1 == ub_i or lb_i == ub_i
    assert arr[lb_i] <= val <= arr[ub_i]

    return lb_i, ub_i


#################################################################


#################################################################
class test_find_lb_ub_in_sorted_arr(unittest.TestCase):
    def test_3_len(self):
        arr = [1, 2, 3]
        for cyclic in [False, True]:
            self.assertEqual(
                find_lb_ub_in_sorted_arr(1, arr, cyclic=cyclic, cyclic_max_val=4), (0, 0)
            )
            self.assertEqual(
                find_lb_ub_in_sorted_arr(1.1, arr, cyclic=cyclic, cyclic_max_val=4), (0, 1)
            )
            self.assertEqual(
                find_lb_ub_in_sorted_arr(2, arr, cyclic=cyclic, cyclic_max_val=4), (0, 1)
            )
            self.assertEqual(
                find_lb_ub_in_sorted_arr(2.3, arr, cyclic=cyclic, cyclic_max_val=4), (1, 2)
            )
            self.assertEqual(
                find_lb_ub_in_sorted_arr(3, arr, cyclic=cyclic, cyclic_max_val=4), (1, 2)
            )
        self.assertEqual(find_lb_ub_in_sorted_arr(3.5, arr, cyclic=True, cyclic_max_val=4), (2, 0))


#################################################################


#################################################################
def function_count_calls(func):
    @functools.wraps(func)
    def decor(*args, **kwargs):
        decor.count += 1
        return func(*args, **kwargs)

    decor.count = 0
    return decor


#################################################################


#################################################################
try:
    import cv2

    @function_count_calls
    def imshow(image, window_name=None):
        if window_name is None:
            window_name = f"Image Window #{imshow.count}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, image)
        plt.show()
        cv2.waitKey()

    def imread(filename):
        im = cv2.imread(filename)
        if im is None:
            exit(f"Could not load image {filename}")
        return im

    def rotate_image(image, angle_in_degrees):
        image_center = tuple(np.array(image.shape[1::-1]) / 2)
        rot_mat = cv2.getRotationMatrix2D(image_center, angle_in_degrees, 1)
        result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
        return result, rot_mat
except:
    pass
#################################################################


#################################################################
class array_without_lesser_or_equal_elements:
    def __init__(self):
        self.array = []

    def add(self, new_element):
        elements_to_keep = [False if x < new_element else True for x in self.array]
        should_add_new_element = True
        new_array = []
        for e, ek in zip(self.array, elements_to_keep):
            if ek:
                new_array.append(e)
                if new_element <= e:
                    should_add_new_element = False
        if should_add_new_element:
            new_array.append(new_element)
        self.array = new_array


class test_array_without_lesser_or_equal_elements(unittest.TestCase):
    def test_with_nums(self):
        a = array_without_lesser_or_equal_elements()
        self.assertEqual(a.array, [])

        a.add(3)
        self.assertEqual(a.array, [3])

        a.add(2)
        self.assertEqual(a.array, [3])

        a.add(5)
        self.assertEqual(a.array, [5])

    def test_with_sets(self):
        a = array_without_lesser_or_equal_elements()
        self.assertEqual(a.array, [])

        a.add(set())
        self.assertEqual(a.array, [set()])

        a.add(set([2]))
        self.assertEqual(a.array, [set([2])])

        a.add(set([2]))
        self.assertEqual(a.array, [set([2])])

        a.add(set([3]))
        self.assertEqual(a.array, [set([2]), set([3])])

        a.add(set([2, 3]))
        self.assertEqual(a.array, [set([2, 3])])

        a.add(set([4]))
        self.assertEqual(a.array, [set([2, 3]), set([4])])

        a.add(set([3]))
        self.assertEqual(a.array, [set([2, 3]), set([4])])

        a.add(set([3, 4, 5]))
        self.assertEqual(a.array, [set([2, 3]), set([3, 4, 5])])


#################################################################

#################################################################
try:
    import dataclasses

    def default_field(obj):
        return dataclasses.field(default_factory=lambda: copy.copy(obj))

except:
    pass
#################################################################


#################################################################
# Usage example:
# from enum import auto
#
#
# class derate_type(o.IndEnum):
#    net = auto()
#    gate = auto()
class IndEnum(enum.IntEnum):
    def _generate_next_value_(self, _start, count, _last_values):
        return count


#################################################################


#################################################################
def df_as_numeric(df):
    return df[df.columns].apply(pd.to_numeric, errors="coerce")


#################################################################


# returns 1-dimensional lattice embedding of the scalar x
# according to the discritization points in vector V
# returns index d and alpha_d such that the embedding is:
# values:  0 0 0 1-alpha_d alpha_d ... 0 0 0
# indices: 0 0 0       d-1       d ... 0 0 0
def lattice_1d_ind_and_alpha(x, v):
    assert np.all(np.diff(v) > 0)  # strictly sorted
    assert v[0] <= x <= v[-1]

    d = 1
    while d <= len(v) - 2 and x >= v[d]:
        d += 1

    x_hat = (x - v[d - 1]) / (v[d] - v[d - 1])

    return d, x_hat


# returns full vector of lattice_1d_ind_and_val
def lattice_1d(x, v):
    d, x_hat = lattice_1d_ind_and_alpha(x, v)

    alpha = np.zeros((len(v),))

    alpha[d - 1] = 1 - x_hat
    alpha[d] = x_hat

    return alpha


class test_lattice_1d(unittest.TestCase):
    def test_a(self):
        v = np.array([1, 2, 3])
        with self.assertRaises(AssertionError):
            lattice_1d(0.9, v)
        np.testing.assert_almost_equal(lattice_1d(1, v), [1, 0, 0])
        np.testing.assert_almost_equal(lattice_1d(1.5, v), [0.5, 0.5, 0])
        np.testing.assert_almost_equal(lattice_1d(2, v), [0, 1, 0])
        np.testing.assert_almost_equal(lattice_1d(3, v), [0, 0, 1])
        with self.assertRaises(AssertionError):
            lattice_1d(3.1, v)


def piecewise_linear_function(v, w, x):
    assert v.ndim == 1
    assert w.ndim == 1
    assert v.shape[0] == w.shape[0]
    d, alpha = lattice_1d_ind_and_alpha(x, v)
    res = alpha * w[d]
    d_prev = d - 1
    if d_prev >= 0:
        res += (1 - alpha) * w[d_prev]
    return res


class test_piecewise_linear_function(unittest.TestCase):
    def test_a(self):
        v = np.array([1, 2, 3])
        w = np.array([20, 10, 30])
        print()
        np.testing.assert_almost_equal(piecewise_linear_function(v, w, 1), 20)
        np.testing.assert_almost_equal(piecewise_linear_function(v, w, 1.1), 19)
        np.testing.assert_almost_equal(piecewise_linear_function(v, w, 2), 10)
        np.testing.assert_almost_equal(piecewise_linear_function(v, w, 2.5), 20)
        np.testing.assert_almost_equal(piecewise_linear_function(v, w, 3), 30)


#################################################################
if __name__ == "__main__":
    unittest.main()
#################################################################

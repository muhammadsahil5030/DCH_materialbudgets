#!/usr/bin/env python3
"""
Plot IDEA Drift Chamber material-budget histograms produced by g4PolarAngleScan.

The Geant4 scan is not repeated here. This script only reads the THStacks stored
in the g4PolarAngleScan ROOT file and redraws them with user-controlled styling.

Expected objects in the input ROOT file:
    hs_x0
    hs_lambda
    hs_depth

Example:
    python material_plots_DCH_g4.py \
        --fname DCH_material_scan.root \
        --angleDef theta \
        --angleMin 10 --angleMax 170 \
        --yMaxX0 7.0 \
        --outputDir DCH_plots_theta

For cos(theta):
    python material_plots_DCH_g4.py \
        --fname DCH_material_scan_cosTheta.root \
        --angleDef cosTheta \
        --angleMin -1 --angleMax 1 \
        --yMaxX0 7.0 \
        --outputDir DCH_plots_cosTheta
"""

import argparse
import os
from pathlib import Path
import ROOT


# =============================================================================
# DCH PLOT CONFIGURATION
# Change these lists/dictionaries if you want a different stack order, labels,
# or colours. The order below is BOTTOM -> TOP in the stack.
# =============================================================================

MATERIAL_ORDER = [
    "CarbonFibStr",
    "GasHe_90Isob_10",
    "PolystyreneFoam",
    "DCH_FSideWireMat",
    "DCH_FCentralWireMat",
    "DCH_SWireMat",
]

MATERIAL_LABELS = {
    "CarbonFibStr": "CarbonFibStr",
    "GasHe_90Isob_10": "GasHe_90Isob_10",
    "PolystyreneFoam": "PolystyreneFoam",
    "DCH_FSideWireMat": "DCH_FSideWireMat",
    "DCH_FCentralWireMat": "DCH_FCentralWireMat",
    "DCH_SWireMat": "DCH_SWireMat",
}

MATERIAL_COLORS = {
    "CarbonFibStr": ROOT.kRed,
    "GasHe_90Isob_10": ROOT.kBlue,
    "PolystyreneFoam": ROOT.kGreen + 2,
    "DCH_FSideWireMat": ROOT.kOrange + 1,
    "DCH_FCentralWireMat": ROOT.kMagenta,
    "DCH_SWireMat": ROOT.kCyan + 1,
}

DEFAULT_UNKNOWN_COLORS = [
    ROOT.kYellow + 2,
    ROOT.kViolet + 1,
    ROOT.kTeal + 2,
    ROOT.kPink + 3,
    ROOT.kAzure + 2,
    ROOT.kSpring + 5,
]

AXIS_TITLES = {
    "theta": "#theta [deg]",
    "thetaRad": "#theta [rad]",
    "cosTheta": "cos(#theta)",
    "eta": "#eta",
}

QUANTITIES = {
    "x0": ("hs_x0", "Material budget x/X_{0} [%]"),
    "lambda": ("hs_lambda", "Number of #lambda_{I}"),
    "depth": ("hs_depth", "Material depth [mm]"),
}


def parse_args():
    p = argparse.ArgumentParser(
        description="Redraw DCH g4PolarAngleScan ROOT stacks with controlled styling."
    )
    p.add_argument("--fname", "-f", required=True, help="g4PolarAngleScan ROOT file")
    p.add_argument(
        "--angleDef",
        choices=["theta", "thetaRad", "cosTheta", "eta"],
        required=True,
        help="Angular variable used in the scan",
    )
    p.add_argument("--angleMin", type=float, default=None, help="Displayed x-axis minimum")
    p.add_argument("--angleMax", type=float, default=None, help="Displayed x-axis maximum")
    p.add_argument(
        "--quantity",
        choices=["x0", "lambda", "depth", "all"],
        default="all",
        help="Quantity to draw (default: x0)",
    )
    p.add_argument("--yMaxX0", type=float, default=None, help="Fixed y maximum for X0 plot")
    p.add_argument("--yMaxLambda", type=float, default=None, help="Fixed y maximum for lambda plot")
    p.add_argument("--yMaxDepth", type=float, default=None, help="Fixed y maximum for depth plot")
    p.add_argument("--outputDir", "-o", default="DCH_plots", help="Output directory")
    p.add_argument(
        "--formats",
        nargs="+",
        default=["pdf", "png", "root"],
        choices=["pdf", "png", "root"],
        help="Output formats (default: pdf png root)",
    )
    p.add_argument(
        "--ignoreMats",
        nargs="+",
        default=[],
        help="Materials to hide at plotting stage (normally Air/Vacuum were already removed in the scan)",
    )
    p.add_argument(
        "--drawTotal",
        action="store_true",
        help="Draw a black total-material line on top of the stack",
    )
    p.add_argument(
        "--legendOutside",
        action="store_true",
        help="Place legend in a dedicated right margin instead of over the data",
    )
    p.add_argument("--canvasWidth", type=int, default=1000)
    p.add_argument("--canvasHeight", type=int, default=700)
    p.add_argument("--legendTextSize", type=float, default=0.035)
    p.add_argument("--axisLabelSize", type=float, default=0.040)
    p.add_argument("--axisTitleSize", type=float, default=0.045)
    p.add_argument(
        "--boldAxisTitles",
        action="store_true",
        help="Use ROOT bold font for x/y axis titles",
    )
    p.add_argument(
        "--prefix",
        default="DCH",
        help="Prefix for output file names (default: DCH)",
    )
    return p.parse_args()


def clone_stack_histograms(fin, stack_name, quantity):
    """Read and clone the histograms stored inside one THStack."""
    stack_in = fin.Get(stack_name)
    if not stack_in:
        raise RuntimeError(f'Cannot find "{stack_name}" in {fin.GetName()}')

    hlist = stack_in.GetHists()
    if not hlist:
        raise RuntimeError(f'THStack "{stack_name}" contains no histograms')

    prefix = f"h_{quantity}_"
    out = {}
    for obj in hlist:
        name = obj.GetName()
        material = name[len(prefix):] if name.startswith(prefix) else name
        h = obj.Clone(f"plot_{name}")
        h.SetDirectory(0)

        # Convert radiation-length fraction x/X0 to percent for plotting.
        if quantity == "x0":
            h.Scale(100.0)

        out[material] = h
    return out


def ordered_materials(histograms, ignored):
    """Known DCH materials first, then any unexpected materials from the ROOT file."""
    ignored = set(ignored)
    ordered = [m for m in MATERIAL_ORDER if m in histograms and m not in ignored]
    extras = sorted(m for m in histograms if m not in ordered and m not in ignored)
    return ordered + extras


def apply_hist_style(hist, material, extra_index=0):
    if material in MATERIAL_COLORS:
        color = MATERIAL_COLORS[material]
    else:
        color = DEFAULT_UNKNOWN_COLORS[extra_index % len(DEFAULT_UNKNOWN_COLORS)]

    hist.SetFillColor(color)
    hist.SetFillStyle(1001)
    hist.SetLineColor(ROOT.kBlack)
    hist.SetLineWidth(1)


def make_total(histograms, materials, quantity):
    if not materials:
        return None
    total = histograms[materials[0]].Clone(f"plot_h_{quantity}_TOTAL")
    total.Reset("ICES")
    total.SetDirectory(0)
    for mat in materials:
        total.Add(histograms[mat])
    total.SetFillStyle(0)
    total.SetLineColor(ROOT.kBlack)
    total.SetLineWidth(2)
    return total


def configure_axes(stack, args, y_title, y_max):
    xaxis = stack.GetXaxis()
    yaxis = stack.GetYaxis()

    xaxis.SetTitle(AXIS_TITLES[args.angleDef])
    yaxis.SetTitle(y_title)

    # ROOT fonts: 42 normal Helvetica, 62 bold Helvetica
    title_font = 62 if args.boldAxisTitles else 42
    xaxis.SetTitleFont(title_font)
    yaxis.SetTitleFont(title_font)
    xaxis.SetLabelFont(42)
    yaxis.SetLabelFont(42)

    xaxis.SetTitleSize(args.axisTitleSize)
    yaxis.SetTitleSize(args.axisTitleSize)
    xaxis.SetLabelSize(args.axisLabelSize)
    yaxis.SetLabelSize(args.axisLabelSize)

    xaxis.SetTitleOffset(1.05)
    yaxis.SetTitleOffset(1.20)

    xaxis.SetNdivisions(510)
    yaxis.SetNdivisions(510)

    if args.angleMin is not None or args.angleMax is not None:
        xmin = args.angleMin if args.angleMin is not None else xaxis.GetXmin()
        xmax = args.angleMax if args.angleMax is not None else xaxis.GetXmax()
        xaxis.SetRangeUser(xmin, xmax)

    stack.SetMinimum(0.0)
    if y_max is not None:
        stack.SetMaximum(y_max)


def draw_one(fin, quantity, args, outdir):
    stack_name, y_title = QUANTITIES[quantity]
    histograms = clone_stack_histograms(fin, stack_name, quantity)
    materials = ordered_materials(histograms, args.ignoreMats)

    if not materials:
        raise RuntimeError(f"No materials remain for quantity {quantity}")

    # New stack: this is what gives us full control over order and decoration.
    stack = ROOT.THStack(f"DCH_{quantity}_stack", f";{AXIS_TITLES[args.angleDef]};{y_title}")

    extra_idx = 0
    for mat in materials:
        apply_hist_style(histograms[mat], mat, extra_idx)
        if mat not in MATERIAL_COLORS:
            extra_idx += 1
        stack.Add(histograms[mat], "hist")

    c = ROOT.TCanvas(
        f"c_DCH_{quantity}_{args.angleDef}",
        f"DCH {quantity}",
        args.canvasWidth,
        args.canvasHeight,
    )

    c.SetTopMargin(0.06)
    c.SetBottomMargin(0.12)
    c.SetLeftMargin(0.13)

    if args.legendOutside:
        c.SetRightMargin(0.31)
        leg = ROOT.TLegend(0.70, 0.58, 0.985, 0.91)
    else:
        c.SetRightMargin(0.05)
        leg = ROOT.TLegend(0.32, 0.72, 0.68, 0.91)

    c.SetTicks(1, 1)

    stack.Draw("hist")

    y_max = {
        "x0": args.yMaxX0,
        "lambda": args.yMaxLambda,
        "depth": args.yMaxDepth,
    }[quantity]
    configure_axes(stack, args, y_title, y_max)

    total = None
    if args.drawTotal:
        total = make_total(histograms, materials, quantity)
        total.Draw("hist same")

    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.SetTextFont(42)
    leg.SetTextSize(args.legendTextSize)

    # Legend is TOP -> BOTTOM, therefore reverse the stack order.
    for mat in reversed(materials):
        leg.AddEntry(histograms[mat], MATERIAL_LABELS.get(mat, mat), "f")
    if total:
        leg.AddEntry(total, "Total", "l")
    leg.Draw()

    c.Modified()
    c.Update()

    # If no fixed y maximum was requested, add a little headroom after drawing.
    if y_max is None:
        ymax_auto = stack.GetMaximum()
        stack.SetMaximum(1.08 * ymax_auto if ymax_auto > 0 else 1.0)
        c.Modified()
        c.Update()

    stem = f"{args.prefix}_{quantity}_{args.angleDef}"
    for fmt in args.formats:
        c.SaveAs(os.fspath(outdir / f"{stem}.{fmt}"))

    print(f"Created: {outdir / stem}.[{'/'.join(args.formats)}]")


def main():
    args = parse_args()

    ROOT.gROOT.SetBatch(True)
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetOptTitle(0)
    ROOT.gStyle.SetPadTickX(1)
    ROOT.gStyle.SetPadTickY(1)
    ROOT.gStyle.SetLineWidth(1)

    outdir = Path(args.outputDir)
    outdir.mkdir(parents=True, exist_ok=True)

    fin = ROOT.TFile.Open(args.fname, "READ")
    if not fin or fin.IsZombie():
        raise RuntimeError(f"Cannot open ROOT file: {args.fname}")

    quantities = list(QUANTITIES) if args.quantity == "all" else [args.quantity]
    for q in quantities:
        draw_one(fin, q, args, outdir)

    fin.Close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Plot IDEA material-budget contributions from independent g4PolarAngleScan ROOT files.

The script reads one ROOT file per subdetector. For each subdetector it sums all
material histograms stored inside the g4PolarAngleScan THStack, giving one
subdetector-level contribution. These detector totals are then stacked.

Default input files:
    Tracking_beamPipe_material_scan.root
    Tracking_vertex_material_scan.root
    Tracking_DCH_material_scan.root
    Tracking_SiliconWrapper_material_scan.root
    material_scan_endPlateAbsorber.root
    material_scan_solenoid.root
    material_scan_preshower.root

Expected THStacks in each ROOT file:
    hs_x0
    hs_lambda
    hs_depth

All input scans MUST have identical angular definition, range and binning.

Example (theta):
    python material_plots_IDEA_g4.py \
        --angleDef theta \
        --angleMin 0 --angleMax 180 \
        --outputDir IDEA_plots_theta

Example (cosTheta):
    python material_plots_IDEA_g4.py \
        --angleDef cosTheta \
        --angleMin -1 --angleMax 1 \
        --outputDir IDEA_plots_cosTheta
"""

import argparse
import math
import os
from pathlib import Path

import ROOT


# =============================================================================
# SUBDETECTOR CONFIGURATION
# Order here is BOTTOM -> TOP in the stacked histogram.
# =============================================================================

DETECTOR_ORDER = [
    "BeamPipe",
    "Vertex",
    "DCH",
    "SiliconWrapper",
    "EndPlateAbsorber",
    "Solenoid",
    "Preshower",
]

DETECTOR_LABELS = {
    "BeamPipe": "Beam Pipe",
    "Vertex": "Vertex",
    "DCH": "Drift Chamber",
    "SiliconWrapper": "Silicon Wrapper",
    "EndPlateAbsorber": "End Plate Absorber",
    "Solenoid": "Solenoid",
    "Preshower": "Preshower",
}

DETECTOR_COLORS = {
    "BeamPipe": ROOT.kGray + 1,
    "Vertex": ROOT.kOrange + 1,
    "DCH": ROOT.kAzure + 1,
    "SiliconWrapper": ROOT.kGreen + 2,
    "EndPlateAbsorber": ROOT.kViolet + 1,
    "Solenoid": ROOT.kRed + 1,
    "Preshower": ROOT.kCyan + 1,
}

AXIS_TITLES = {
    "theta": "#theta [deg]",
    "thetaRad": "#theta [rad]",
    "cosTheta": "cos(#theta)",
    "eta": "#eta",
}

QUANTITIES = {
    "x0": ("hs_x0", "Number of X_{0}"),
    "lambda": ("hs_lambda", "Number of #lambda_{I}"),
    "depth": ("hs_depth", "Material depth [mm]"),
}


# =============================================================================
# Command-line arguments
# =============================================================================


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Plot IDEA subdetector-by-subdetector material budget from "
            "g4PolarAngleScan ROOT files."
        )
    )

    # Exact filenames currently used by the user.
    p.add_argument(
        "--beamPipe",
        default="Tracking_beamPipe_material_scan.root",
        help="Beam-pipe ROOT file",
    )
    p.add_argument(
        "--vertex",
        default="Tracking_vertex_material_scan.root",
        help="Vertex ROOT file",
    )
    p.add_argument(
        "--dch",
        default="Tracking_DCH_material_scan.root",
        help="DCH ROOT file",
    )
    p.add_argument(
        "--siliconWrapper",
        default="Tracking_SiliconWrapper_material_scan.root",
        help="Silicon-wrapper ROOT file",
    )
    p.add_argument(
        "--endPlateAbsorber",
        default="material_scan_endPlateAbsorber.root",
        help="End-plate absorber ROOT file",
    )
    p.add_argument(
        "--solenoid",
        default="material_scan_solenoid.root",
        help="Solenoid ROOT file",
    )
    p.add_argument(
        "--preshower",
        default="material_scan_preshower.root",
        help="Preshower ROOT file",
    )

    p.add_argument(
        "--angleDef",
        choices=["theta", "thetaRad", "cosTheta", "eta"],
        required=True,
        help="Angular variable used when ALL scans were produced",
    )
    p.add_argument(
        "--angleMin",
        type=float,
        default=None,
        help="Displayed x-axis minimum; default: stored ROOT minimum",
    )
    p.add_argument(
        "--angleMax",
        type=float,
        default=None,
        help="Displayed x-axis maximum; default: stored ROOT maximum",
    )

    p.add_argument(
        "--quantity",
        choices=["x0", "lambda", "depth", "all"],
        default="all",
        help="Quantity to draw (default: all)",
    )

    p.add_argument("--yMaxX0", type=float, default=None, help="Fixed y maximum for X0")
    p.add_argument(
        "--yMaxLambda",
        type=float,
        default=None,
        help="Fixed y maximum for interaction length",
    )
    p.add_argument(
        "--yMaxDepth",
        type=float,
        default=None,
        help="Fixed y maximum for material depth",
    )

    p.add_argument(
        "--ignoreMats",
        nargs="+",
        default=[],
        help=(
            "Material names to ignore while summing each subdetector. "
            "Normally Air/Vacuum were already ignored during the scan."
        ),
    )

    p.add_argument(
        "--drawTotal",
        action="store_true",
        help="Draw a black total-material line on top of the stack",
    )

    p.add_argument(
        "--outputDir",
        "-o",
        default="IDEA_plots",
        help="Output directory",
    )
    p.add_argument(
        "--prefix",
        default="IDEA",
        help="Output filename prefix (default: IDEA)",
    )
    p.add_argument(
        "--formats",
        nargs="+",
        default=["pdf", "png", "root"],
        choices=["pdf", "png", "root"],
        help="Output formats (default: pdf png root)",
    )

    p.add_argument("--canvasWidth", type=int, default=1100)
    p.add_argument("--canvasHeight", type=int, default=700)
    p.add_argument("--legendTextSize", type=float, default=0.027)
    p.add_argument("--legendColumns", type=int, default=4)
    p.add_argument("--axisLabelSize", type=float, default=0.040)
    p.add_argument("--axisTitleSize", type=float, default=0.045)
    p.add_argument(
        "--normalAxisTitles",
        action="store_true",
        help="Use normal rather than bold axis-title font",
    )

    return p.parse_args()


# =============================================================================
# ROOT helpers
# =============================================================================


def open_root(path):
    f = ROOT.TFile.Open(str(path), "READ")
    if not f or f.IsZombie():
        raise RuntimeError(f"Cannot open ROOT file: {path}")
    return f


def material_name_from_hist(hist_name, quantity):
    prefix = f"h_{quantity}_"
    if hist_name.startswith(prefix):
        return hist_name[len(prefix):]
    return hist_name


def detector_total_from_stack(fin, stack_name, quantity, detector_name, ignored_materials):
    """
    Sum all per-material histograms in a g4PolarAngleScan THStack.
    Returns one TH1D for the total contribution of this subdetector.
    """
    stack = fin.Get(stack_name)
    if not stack:
        raise RuntimeError(f'Cannot find "{stack_name}" in {fin.GetName()}')

    hlist = stack.GetHists()
    if not hlist or hlist.GetSize() == 0:
        raise RuntimeError(f'THStack "{stack_name}" in {fin.GetName()} contains no histograms')

    ignored = set(ignored_materials)
    total = None
    used_materials = []

    for obj in hlist:
        material = material_name_from_hist(obj.GetName(), quantity)
        if material in ignored:
            continue

        if total is None:
            total = obj.Clone(f"h_{quantity}_{detector_name}")
            total.Reset("ICES")
            total.SetDirectory(0)

        total.Add(obj)
        used_materials.append(material)

    if total is None:
        raise RuntimeError(
            f"No materials remain for {detector_name}, quantity={quantity}, "
            f"file={fin.GetName()}"
        )

    return total, used_materials


def hist_edges(hist):
    """Return all x-bin edges including the final upper edge."""
    ax = hist.GetXaxis()
    n = hist.GetNbinsX()
    return [ax.GetBinLowEdge(i) for i in range(1, n + 1)] + [ax.GetBinUpEdge(n)]


def validate_compatible_histograms(detector_hists, quantity):
    """Require exactly compatible x binning for every subdetector file."""
    ref_name = DETECTOR_ORDER[0]
    ref = detector_hists[ref_name]
    ref_edges = hist_edges(ref)

    for det in DETECTOR_ORDER[1:]:
        h = detector_hists[det]

        if h.GetNbinsX() != ref.GetNbinsX():
            raise RuntimeError(
                f"Incompatible {quantity} binning: {ref_name} has "
                f"{ref.GetNbinsX()} bins, but {det} has {h.GetNbinsX()} bins. "
                "Re-run all scans with identical angle range and bin width."
            )

        edges = hist_edges(h)
        for a, b in zip(ref_edges, edges):
            if not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9):
                raise RuntimeError(
                    f"Incompatible {quantity} x-axis binning between {ref_name} and {det}. "
                    "All g4PolarAngleScan jobs must use the same --angleDef, "
                    "--minValue, --maxValue and -b."
                )


def make_grand_total(detector_hists, quantity):
    total = detector_hists[DETECTOR_ORDER[0]].Clone(f"h_{quantity}_IDEA_TOTAL")
    total.Reset("ICES")
    total.SetDirectory(0)

    for det in DETECTOR_ORDER:
        total.Add(detector_hists[det])

    total.SetFillStyle(0)
    total.SetLineColor(ROOT.kBlack)
    total.SetLineWidth(2)
    return total


# =============================================================================
# Plot styling
# =============================================================================


def style_detector_hist(hist, detector):
    hist.SetFillColor(DETECTOR_COLORS[detector])
    hist.SetFillStyle(1001)
    hist.SetLineColor(ROOT.kBlack)
    hist.SetLineWidth(1)


def configure_axes(stack, args, y_title, y_max, stored_xmin, stored_xmax):
    xaxis = stack.GetXaxis()
    yaxis = stack.GetYaxis()

    xaxis.SetTitle(AXIS_TITLES[args.angleDef])
    yaxis.SetTitle(y_title)

    title_font = 42 if args.normalAxisTitles else 62
    xaxis.SetTitleFont(title_font)
    yaxis.SetTitleFont(title_font)
    xaxis.SetLabelFont(42)
    yaxis.SetLabelFont(42)

    xaxis.SetTitleSize(args.axisTitleSize)
    yaxis.SetTitleSize(args.axisTitleSize)
    xaxis.SetLabelSize(args.axisLabelSize)
    yaxis.SetLabelSize(args.axisLabelSize)

    xaxis.SetTitleOffset(1.05)
    yaxis.SetTitleOffset(1.25)

    xaxis.SetNdivisions(510)
    yaxis.SetNdivisions(510)

    xmin = args.angleMin if args.angleMin is not None else stored_xmin
    xmax = args.angleMax if args.angleMax is not None else stored_xmax

    if xmin < stored_xmin - 1e-9:
        print(
            f"WARNING: requested angleMin={xmin:g}, but ROOT histograms start at "
            f"{stored_xmin:g}. Using {stored_xmin:g}."
        )
        xmin = stored_xmin

    if xmax > stored_xmax + 1e-9:
        print(
            f"WARNING: requested angleMax={xmax:g}, but ROOT histograms end at "
            f"{stored_xmax:g}. Using {stored_xmax:g}."
        )
        xmax = stored_xmax

    if xmin >= xmax:
        raise RuntimeError(f"Invalid displayed x range: {xmin} to {xmax}")

    xaxis.SetRangeUser(xmin, xmax)

    stack.SetMinimum(0.0)
    if y_max is not None:
        stack.SetMaximum(y_max)


# =============================================================================
# Draw one quantity
# =============================================================================


def draw_one(files, quantity, args, outdir):
    stack_name, y_title = QUANTITIES[quantity]
    detector_hists = {}

    print(f"\n--- {quantity} ---")
    for detector in DETECTOR_ORDER:
        h, materials = detector_total_from_stack(
            files[detector],
            stack_name,
            quantity,
            detector,
            args.ignoreMats,
        )
        detector_hists[detector] = h
        print(
            f"{DETECTOR_LABELS[detector]:<20s}: "
            f"{len(materials):2d} material histograms summed"
        )

    validate_compatible_histograms(detector_hists, quantity)

    ref = detector_hists[DETECTOR_ORDER[0]]
    stored_xmin = ref.GetXaxis().GetXmin()
    stored_xmax = ref.GetXaxis().GetXmax()

    print(
        f"Common x range: {stored_xmin:g} to {stored_xmax:g}; "
        f"bins = {ref.GetNbinsX()}"
    )

    stack = ROOT.THStack(
        f"IDEA_{quantity}_stack",
        f";{AXIS_TITLES[args.angleDef]};{y_title}",
    )

    for detector in DETECTOR_ORDER:
        style_detector_hist(detector_hists[detector], detector)
        stack.Add(detector_hists[detector], "hist")

    c = ROOT.TCanvas(
        f"c_IDEA_{quantity}_{args.angleDef}",
        f"IDEA {quantity}",
        args.canvasWidth,
        args.canvasHeight,
    )

    c.SetTopMargin(0.08)
    c.SetBottomMargin(0.12)
    c.SetLeftMargin(0.13)
    c.SetRightMargin(0.05)
    c.SetTicks(1, 1)

    stack.Draw("hist")

    y_max = {
        "x0": args.yMaxX0,
        "lambda": args.yMaxLambda,
        "depth": args.yMaxDepth,
    }[quantity]

    configure_axes(
        stack,
        args,
        y_title,
        y_max,
        stored_xmin,
        stored_xmax,
    )

    total = None
    if args.drawTotal:
        total = make_grand_total(detector_hists, quantity)
        total.Draw("hist same")

    # Wide, upper-centre legend. Four columns gives two rows for seven detectors.
    leg = ROOT.TLegend(0.12, 0.80, 0.88, 0.94)
    leg.SetNColumns(args.legendColumns)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.SetTextFont(42)
    leg.SetTextSize(args.legendTextSize)

    # Reverse order so legend follows visible top -> bottom stack layering.
    for detector in reversed(DETECTOR_ORDER):
        leg.AddEntry(
            detector_hists[detector],
            DETECTOR_LABELS[detector],
            "f",
        )

    if total:
        leg.AddEntry(total, "Total", "l")

    leg.Draw()

    c.Modified()
    c.Update()

    # Leave extra vertical headroom because the legend sits above the stack.
    if y_max is None:
        ymax_auto = stack.GetMaximum()
        stack.SetMaximum(1.22 * ymax_auto if ymax_auto > 0 else 1.0)
        c.Modified()
        c.Update()

    stem = f"{args.prefix}_{quantity}_{args.angleDef}"
    for fmt in args.formats:
        outfile = outdir / f"{stem}.{fmt}"
        c.SaveAs(os.fspath(outfile))

    print(f"Created: {outdir / stem}.[{'/'.join(args.formats)}]")


# =============================================================================
# Main
# =============================================================================


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

    input_paths = {
        "BeamPipe": Path(args.beamPipe),
        "Vertex": Path(args.vertex),
        "DCH": Path(args.dch),
        "SiliconWrapper": Path(args.siliconWrapper),
        "EndPlateAbsorber": Path(args.endPlateAbsorber),
        "Solenoid": Path(args.solenoid),
        "Preshower": Path(args.preshower),
    }

    print("\nInput files:")
    for detector in DETECTOR_ORDER:
        path = input_paths[detector]
        if not path.is_file():
            raise RuntimeError(
                f"Missing {DETECTOR_LABELS[detector]} ROOT file: {path}"
            )
        print(f"  {DETECTOR_LABELS[detector]:<20s}: {path}")

    files = {detector: open_root(path) for detector, path in input_paths.items()}

    try:
        quantities = list(QUANTITIES) if args.quantity == "all" else [args.quantity]
        for quantity in quantities:
            draw_one(files, quantity, args, outdir)
    finally:
        for f in files.values():
            f.Close()


if __name__ == "__main__":
    main()

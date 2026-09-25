#!/usr/bin/env python3
"""
Plot only the IDEA DCH wire material contributions from a g4PolarAngleScan ROOT file.

Produces:
  1) stacked wire plot
  2) non-stacked overlay plot

No scan is repeated; the binning is taken directly from the ROOT histograms.

cosTheta and theta running commands:
python material_wiresOnlyplots_DCH_g4.py \
    --fname g4PolarAngle_material_Scan.root \
    --angleDef cosTheta \
    --angleMin 0.0 \
    --angleMax 1.0 \
    --quantity all \
    --drawTotal \
    --outputDir wires_cosTheta

python material_wiresOnlyplots_DCH_g4.py \
    --fname g4PolarAngle_material_Scan.root \
    --angleDef theta \
    --angleMin 0.0 \
    --angleMax 90.0 \
    --quantity all \
    --drawTotal \
    --outputDir wires_theta
"""

import argparse
from pathlib import Path
import ROOT


WIRE_MATERIALS = [
    "DCH_FSideWireMat",
    "DCH_FCentralWireMat",
    "DCH_SWireMat",
]

WIRE_LABELS = {
    "DCH_FSideWireMat": "Field side wires",
    "DCH_FCentralWireMat": "Field central wires",
    "DCH_SWireMat": "Sense wires",
}

WIRE_COLORS = {
    "DCH_FSideWireMat": ROOT.kOrange + 1,
    "DCH_FCentralWireMat": ROOT.kMagenta,
    "DCH_SWireMat": ROOT.kCyan + 1,
}

QUANTITIES = {
    "x0": ("hs_x0", "Material Budget /X_{0} [%]"),
    "lambda": ("hs_lambda", "Number of #lambda_{I}"),
    "depth": ("hs_depth", "Material depth [mm]"),
}

X_TITLES = {
    "theta": "#theta [deg]",
    "thetaRad": "#theta [rad]",
    "cosTheta": "cos(#theta)",
    "eta": "#eta",
}


def parse_args():
    p = argparse.ArgumentParser(description="Plot DCH wire material budget only.")
    p.add_argument("--fname", "-f", required=True)
    p.add_argument(
        "--angleDef",
        choices=["theta", "thetaRad", "cosTheta", "eta"],
        required=True,
    )
    p.add_argument("--angleMin", type=float, default=None)
    p.add_argument("--angleMax", type=float, default=None)
    p.add_argument(
        "--quantity",
        choices=["x0", "lambda", "depth", "all"],
        default="x0",
    )
    p.add_argument("--outputDir", "-o", default="wires")
    p.add_argument("--prefix", default="DCH_wires")
    p.add_argument("--drawTotal", action="store_true")
    return p.parse_args()


def get_wire_histograms(fin, stack_name, quantity):
    stack = fin.Get(stack_name)
    if not stack:
        raise RuntimeError(f'Cannot find "{stack_name}" in ROOT file.')

    histograms = {}
    prefix = f"h_{quantity}_"

    for obj in stack.GetHists():
        name = obj.GetName()
        material = name[len(prefix):] if name.startswith(prefix) else name

        if material in WIRE_MATERIALS:
            h = obj.Clone(f"{name}_wire")
            h.SetDirectory(0)
            h.Scale(100.0)
            histograms[material] = h

    missing = [m for m in WIRE_MATERIALS if m not in histograms]
    if missing:
        print("WARNING: missing wire materials:", ", ".join(missing))

    return histograms


def make_total(histograms, quantity):
    mats = [m for m in WIRE_MATERIALS if m in histograms]
    if not mats:
        return None

    total = histograms[mats[0]].Clone(f"h_{quantity}_total_wires")
    total.Reset("ICES")
    total.SetDirectory(0)

    for mat in mats:
        total.Add(histograms[mat])

    total.SetLineColor(ROOT.kBlack)
    total.SetLineWidth(3)
    total.SetFillStyle(0)
    return total


def set_axes(stack, args, y_title):
    stack.GetXaxis().SetTitle(X_TITLES[args.angleDef])
    stack.GetYaxis().SetTitle(y_title)

    if args.angleMin is not None or args.angleMax is not None:
        xmin = args.angleMin if args.angleMin is not None else stack.GetXaxis().GetXmin()
        xmax = args.angleMax if args.angleMax is not None else stack.GetXaxis().GetXmax()
        stack.GetXaxis().SetRangeUser(xmin, xmax)

    stack.SetMinimum(0.0)


def save(canvas, outdir, stem):
    canvas.SaveAs(str(outdir / f"{stem}.pdf"))
    canvas.SaveAs(str(outdir / f"{stem}.png"))

def draw_plot_header():
    latex = ROOT.TLatex()
    latex.SetNDC(True)

    # Main title
    latex.SetTextFont(62)
    latex.SetTextSize(0.045)
    latex.DrawLatex(0.13, 0.94, "IDEA Drift Chamber")


def draw_stacked(histograms, quantity, y_title, args, outdir):
    stack = ROOT.THStack(
        f"wire_stack_{quantity}",
        f";{X_TITLES[args.angleDef]};{y_title}",
    )

    for mat in WIRE_MATERIALS:
        if mat not in histograms:
            continue

        h = histograms[mat].Clone(f"{histograms[mat].GetName()}_stack")
        h.SetDirectory(0)
        h.SetFillColor(WIRE_COLORS[mat])
        h.SetLineColor(ROOT.kBlack)
        stack.Add(h, "hist")

    c = ROOT.TCanvas(f"c_stack_{quantity}", "", 1000, 700)
    c.SetLeftMargin(0.13)
    c.SetBottomMargin(0.12)
    c.SetTicks(1, 1)

    stack.Draw("hist")
    set_axes(stack, args, y_title)

    total = None
    if args.drawTotal:
        total = make_total(histograms, quantity)
        if total:
            total.Draw("hist same")

    leg = ROOT.TLegend(0.52, 0.70, 0.88, 0.90)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    for mat in reversed(WIRE_MATERIALS):
        if mat in histograms:
            leg.AddEntry(histograms[mat], WIRE_LABELS[mat], "f")

    if total:
        leg.AddEntry(total, "Total wires", "l")

    leg.Draw()
    draw_plot_header()
    c.Update()
    stack.SetMaximum(1.10 * stack.GetMaximum())
    c.Update()

    save(c, outdir, f"{args.prefix}_{quantity}_{args.angleDef}_stacked")


def draw_overlay(histograms, quantity, y_title, args, outdir):
    stack = ROOT.THStack(
        f"wire_overlay_{quantity}",
        f";{X_TITLES[args.angleDef]};{y_title}",
    )

    drawn = {}

    for mat in WIRE_MATERIALS:
        if mat not in histograms:
            continue

        h = histograms[mat].Clone(f"{histograms[mat].GetName()}_overlay")
        h.SetDirectory(0)
        h.SetFillStyle(0)
        h.SetLineColor(WIRE_COLORS[mat])
        h.SetLineWidth(3)

        stack.Add(h, "hist")
        drawn[mat] = h

    c = ROOT.TCanvas(f"c_overlay_{quantity}", "", 1000, 700)
    c.SetLeftMargin(0.13)
    c.SetBottomMargin(0.12)
    c.SetTicks(1, 1)

    # "nostack" means every wire contribution starts from zero.
    stack.Draw("nostack hist")
    set_axes(stack, args, y_title)

    total = None
    if args.drawTotal:
        total = make_total(histograms, quantity)
        if total:
            total.SetLineStyle(2)
            total.Draw("hist same")

    leg = ROOT.TLegend(0.52, 0.70, 0.88, 0.90)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)

    for mat in WIRE_MATERIALS:
        if mat in drawn:
            leg.AddEntry(drawn[mat], WIRE_LABELS[mat], "l")

    if total:
        leg.AddEntry(total, "Total wires", "l")

    leg.Draw()
    draw_plot_header()
    ymax = max(
        [h.GetMaximum() for h in drawn.values()]
        + ([total.GetMaximum()] if total else [0.0])
    )
    stack.SetMaximum(1.10 * ymax if ymax > 0 else 1.0)

    c.Update()

    save(c, outdir, f"{args.prefix}_{quantity}_{args.angleDef}_overlay")


def main():
    args = parse_args()

    ROOT.gROOT.SetBatch(True)
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetOptTitle(0)

    outdir = Path(args.outputDir)
    outdir.mkdir(parents=True, exist_ok=True)

    fin = ROOT.TFile.Open(args.fname, "READ")
    if not fin or fin.IsZombie():
        raise RuntimeError(f"Cannot open ROOT file: {args.fname}")

    quantities = list(QUANTITIES) if args.quantity == "all" else [args.quantity]

    for quantity in quantities:
        stack_name, y_title = QUANTITIES[quantity]
        histograms = get_wire_histograms(fin, stack_name, quantity)

        if not histograms:
            raise RuntimeError(f"No wire materials found for {quantity}")

        draw_stacked(histograms, quantity, y_title, args, outdir)
        draw_overlay(histograms, quantity, y_title, args, outdir)

    fin.Close()


if __name__ == "__main__":
    main()

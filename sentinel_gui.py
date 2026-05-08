#!/usr/bin/env python3
"""
CrystalZip Sentinel GUI MVP

A small local desktop interface using Python's built-in tkinter.

Run:
    python3 sentinel_gui.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


HERE = Path(__file__).resolve().parent
SENTINEL = HERE / "sentinel.py"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("CrystalZip Sentinel")
        root.geometry("780x560")

        self.target = tk.StringVar()
        self.output = tk.StringVar(value=str(HERE / "CrystalZip_Archives"))

        frm = tk.Frame(root, padx=12, pady=12)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="Target folder/file").grid(row=0, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.target, width=72).grid(row=1, column=0, sticky="ew")
        tk.Button(frm, text="Browse", command=self.browse_target).grid(row=1, column=1, padx=8)

        tk.Label(frm, text="Archive output folder").grid(row=2, column=0, sticky="w", pady=(12, 0))
        tk.Entry(frm, textvariable=self.output, width=72).grid(row=3, column=0, sticky="ew")
        tk.Button(frm, text="Browse", command=self.browse_output).grid(row=3, column=1, padx=8)

        btns = tk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, sticky="w", pady=12)
        tk.Button(btns, text="Scan for savings", command=self.scan).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="Compress safely", command=self.compress).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="Restore archive", command=self.restore).pack(side="left", padx=(0, 8))

        self.log = scrolledtext.ScrolledText(frm, height=24)
        self.log.grid(row=5, column=0, columnspan=2, sticky="nsew")

        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(5, weight=1)

        self.write("CrystalZip Sentinel ready.\nFiles stay local. Originals are not deleted by default.\n")

    def write(self, text: str):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def run(self, args):
        proc = subprocess.run([sys.executable, str(SENTINEL), *args], capture_output=True, text=True)
        if proc.stdout:
            self.write(proc.stdout)
        if proc.stderr:
            self.write("ERROR:\n" + proc.stderr)
        if proc.returncode != 0:
            messagebox.showerror("CrystalZip Sentinel", "Command failed. See log.")
        return proc

    def browse_target(self):
        path = filedialog.askdirectory(title="Choose folder")
        if not path:
            path = filedialog.askopenfilename(title="Choose file")
        if path:
            self.target.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(title="Choose archive output folder")
        if path:
            self.output.set(path)

    def scan(self):
        target = self.target.get().strip()
        if not target:
            messagebox.showwarning("CrystalZip Sentinel", "Choose a target first.")
            return
        self.write(f"Scanning: {target}")
        self.run(["scan", target])

    def compress(self):
        target = self.target.get().strip()
        output = self.output.get().strip()
        if not target or not output:
            messagebox.showwarning("CrystalZip Sentinel", "Choose target and output folder first.")
            return
        self.write(f"Compressing safely: {target}")
        self.run(["compress", target, "-o", output])

    def restore(self):
        archive = filedialog.askopenfilename(title="Choose .cz archive", filetypes=[("CrystalZip archives", "*.cz"), ("All files", "*.*")])
        if not archive:
            return
        out = filedialog.askdirectory(title="Choose restore folder")
        if not out:
            return
        self.write(f"Restoring: {archive}")
        self.run(["restore", archive, "-o", out])


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()

import tkinter as tk
from tkinter import messagebox, ttk
#./run.sh
FONT = "DejaVu Sans"
DRIFT_TOLERANCE = 1.0   # percentage points treated as "on target"
BAR_SCALE = 10.0        # drift bars span +/- this many percentage points

CLASSES = ["US Equity", "Ex-US Equity", "Bond"]

# name, price (£), shares held, asset class
DEFAULT_HOLDINGS = [
    ("VUSA – S&P 500", "", "", "US Equity"),
    ("XUSE – World ex-US", "", "", "Ex-US Equity"),
    ("AGBP – Global Agg Bond", "", "", "Bond"),
]


def parse_num(text):
    return float(text.replace("£", "").replace(",", "").strip() or 0)


class ShareAllocator:
    def __init__(self, root):
        self.root = root
        self.root.title("ISA Allocator")
        self.root.geometry("1280x860")
        self.root.minsize(1100, 700)

        self.c = {
            "bg": "#0b0d10",
            "card": "#14171c",
            "card2": "#1b1f26",
            "border": "#262b33",
            "fg": "#f3f4f6",
            "muted": "#8b93a1",
            "accent": "#22c55e",
            "under": "#60a5fa",
            "over": "#f59e0b",
            "bad": "#f87171",
            "entry": "#0f1217",
        }
        self.root.configure(bg=self.c["bg"])
        self._style()

        self.rows = []
        self.calculated = False
        self._build_ui()
        self._placeholder()

    # ---------------- Styling / small widgets ----------------

    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(
            "Dark.TCombobox",
            fieldbackground=self.c["entry"], background=self.c["card2"],
            foreground=self.c["fg"], arrowcolor=self.c["muted"],
            bordercolor=self.c["border"], lightcolor=self.c["entry"],
            darkcolor=self.c["entry"], selectbackground=self.c["entry"],
            selectforeground=self.c["fg"],
        )
        s.map("Dark.TCombobox", fieldbackground=[("readonly", self.c["entry"])])
        s.configure(
            "Target.Horizontal.TScale", background=self.c["accent"],
            troughcolor=self.c["entry"], bordercolor=self.c["card"],
            lightcolor=self.c["accent"], darkcolor=self.c["accent"],
        )
        s.map("Target.Horizontal.TScale", background=[("active", "#16a34a")])
        self.root.option_add("*TCombobox*Listbox.background", self.c["card2"])
        self.root.option_add("*TCombobox*Listbox.foreground", self.c["fg"])

    def _label(self, parent, text, size=10, bold=False, fg=None, bg=None, **kw):
        return tk.Label(
            parent, text=text, bg=bg or self.c["card"], fg=fg or self.c["fg"],
            font=(FONT, size, "bold" if bold else "normal"), **kw,
        )

    def _entry(self, parent, value="", width=10, justify="left"):
        e = tk.Entry(
            parent, width=width, bg=self.c["entry"], fg=self.c["fg"],
            insertbackground=self.c["fg"], relief="flat", justify=justify,
            font=(FONT, 10), highlightthickness=1,
            highlightbackground=self.c["border"], highlightcolor=self.c["accent"],
        )
        e.insert(0, value)
        return e

    def _card(self, parent, title=None):
        card = tk.Frame(
            parent, bg=self.c["card"], highlightthickness=1,
            highlightbackground=self.c["border"],
        )
        if title:
            self._label(card, title, 12, True).pack(anchor="w", padx=16, pady=(14, 8))
        return card

    # ---------------- Layout ----------------

    def _build_ui(self):
        header = tk.Frame(self.root, bg=self.c["bg"])
        header.pack(fill="x", padx=20, pady=(18, 10))
        self._label(header, "ISA Allocator", 20, True, bg=self.c["bg"]).pack(anchor="w")
        self._label(
            header, "Invest new money, keep your reserve, stay on target.",
            10, fg=self.c["muted"], bg=self.c["bg"],
        ).pack(anchor="w")

        body = tk.Frame(self.root, bg=self.c["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        left = tk.Frame(body, bg=self.c["bg"])
        left.pack(side="left", fill="y", padx=(0, 14))
        self.right = tk.Frame(body, bg=self.c["bg"])
        self.right.pack(side="left", fill="both", expand=True)

        self._build_cash(left)
        self._build_targets(left)
        self._build_holdings(left)

        tk.Button(
            left, text="Calculate", command=self.calculate, bg=self.c["accent"],
            fg="#04130a", activebackground="#16a34a", relief="flat", bd=0,
            font=(FONT, 11, "bold"), padx=16, pady=10, cursor="hand2",
        ).pack(fill="x", pady=(2, 0))

    def _build_cash(self, parent):
        card = self._card(parent, "Cash")
        card.pack(fill="x", pady=(0, 12))
        grid = tk.Frame(card, bg=self.c["card"])
        grid.pack(fill="x", padx=16, pady=(0, 14))

        self._label(grid, "Cash in account (£)").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_cash = self._entry(grid, "", 14, "right")
        self.entry_cash.grid(row=0, column=1, sticky="e", padx=(16, 0))

        self._label(grid, "Invest now (£)").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_invest = self._entry(grid, "", 14, "right")
        self.entry_invest.grid(row=1, column=1, sticky="e", padx=(16, 0))

        self._label(
            grid, "Anything not invested stays as your reserve.",
            9, fg=self.c["muted"],
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        grid.grid_columnconfigure(0, weight=1)

    def _slider(self, parent, row, left, right, label_var_attr):
        """A 0-100 slider defaulting to 70 with a live 'left x% / right y%' readout."""
        readout = self._label(parent, "", 10, True, fg=self.c["accent"])
        readout.grid(row=row, column=0, sticky="w", pady=(8, 0))

        def update(value):
            v = int(float(value))
            readout.config(text=f"{left} {v}%  /  {right} {100 - v}%")

        scale = ttk.Scale(
            parent, from_=0, to=100, orient="horizontal", command=update,
            style="Target.Horizontal.TScale", length=260,
        )
        scale.set(70)
        update(70)
        scale.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        scale.bind("<ButtonRelease-1>", lambda _e: self._refresh_if_shown())
        setattr(self, label_var_attr, scale)

    def _build_targets(self, parent):
        card = self._card(parent, "Targets")
        card.pack(fill="x", pady=(0, 12))
        grid = tk.Frame(card, bg=self.c["card"])
        grid.pack(fill="x", padx=16, pady=(0, 10))
        grid.grid_columnconfigure(0, weight=1)

        self._slider(grid, 0, "Equities", "Bonds", "entry_equity")
        self._slider(grid, 2, "US", "Ex-US", "entry_us")
        self._label(
            grid, "US / Ex-US applies within the equity part.", 9, fg=self.c["muted"],
        ).grid(row=4, column=0, sticky="w", pady=(2, 0))

    def _refresh_if_shown(self):
        if self.calculated:
            self.calculate()

    def _build_holdings(self, parent):
        card = self._card(parent, "Holdings")
        card.pack(fill="x", pady=(0, 12))
        self.table = tk.Frame(card, bg=self.c["card"])
        self.table.pack(fill="x", padx=16, pady=(0, 14))

        for col, h in enumerate(["Name", "Price £", "Shares", "Class"]):
            self._label(self.table, h, 9, fg=self.c["muted"]).grid(
                row=0, column=col, sticky="w", padx=2, pady=(0, 4))

        for values in DEFAULT_HOLDINGS:
            self._add_row(values)


    def _add_row(self, values):
        row = len(self.rows) + 1
        widths = [20, 8, 7]
        widgets = []
        for col, w in enumerate(widths):
            e = self._entry(self.table, values[col], w, "left" if col == 0 else "right")
            e.grid(row=row, column=col, padx=2, pady=3, ipady=3)
            widgets.append(e)
        cls = ttk.Combobox(
            self.table, values=CLASSES, width=11, state="readonly", style="Dark.TCombobox")
        cls.set(values[3])
        cls.grid(row=row, column=3, padx=2, pady=3)
        widgets.append(cls)
        self.rows.append(widgets)

    # ---------------- Results rendering ----------------

    def _placeholder(self):
        self._label(
            self.right, "Fill in your cash and holdings, then press Calculate.",
            11, fg=self.c["muted"], bg=self.c["bg"],
        ).pack(anchor="nw", pady=8)

    def _clear_results(self):
        for w in self.right.winfo_children():
            w.destroy()

    def _stat_cards(self, items):
        row = tk.Frame(self.right, bg=self.c["bg"])
        row.pack(fill="x", pady=(0, 12))
        for i, (title, value, color) in enumerate(items):
            card = self._card(row)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            row.grid_columnconfigure(i, weight=1, uniform="stat")
            self._label(card, title, 9, fg=self.c["muted"]).pack(anchor="w", padx=14, pady=(10, 0))
            self._label(card, value, 14, True, fg=color).pack(anchor="w", padx=14, pady=(0, 10))

    def _status(self, drift):
        if drift < -DRIFT_TOLERANCE:
            return "Underweight", self.c["under"]
        if drift > DRIFT_TOLERANCE:
            return "Overweight", self.c["over"]
        return "On target", self.c["accent"]

    def _drift_bar(self, parent, drift, color):
        w, h = 160, 14
        cv = tk.Canvas(parent, width=w, height=h, bg=self.c["card"], highlightthickness=0)
        mid = w / 2
        cv.create_rectangle(0, h / 2 - 2, w, h / 2 + 2, fill=self.c["card2"], width=0)
        extent = max(-1.0, min(1.0, drift / BAR_SCALE)) * mid
        cv.create_rectangle(mid, 2, mid + extent, h - 2, fill=color, width=0)
        cv.create_line(mid, 0, mid, h, fill=self.c["muted"])
        return cv

    def _drift_table(self, parent, title, rows):
        """rows: (name, value £, current %, target %)"""
        self._drift_card(parent, title, [(None, rows)])

    def _drift_card(self, parent, title, sections):
        """sections: (subheading or None, rows) – rows as in _drift_table"""
        card = self._card(parent, title)
        card.pack(fill="x", pady=(0, 12))
        for sub, rows in sections:
            if sub:
                self._label(card, sub, 10, fg=self.c["accent"]).pack(
                    anchor="w", padx=16, pady=(0, 2))
            self._drift_grid(card, rows)

    def _drift_grid(self, card, rows):
        grid = tk.Frame(card, bg=self.c["card"])
        grid.pack(fill="x", padx=16, pady=(0, 12))

        heads = ["", "Value", "Now", "Target", "Drift", "", "Status"]
        for col, h in enumerate(heads):
            self._label(grid, h, 9, fg=self.c["muted"]).grid(
                row=0, column=col, sticky="w", padx=6, pady=(0, 4))

        for r, (name, value, cur, tgt) in enumerate(rows, start=1):
            drift = cur - tgt
            status, color = self._status(drift)
            cells = [
                (name, self.c["fg"], True), (f"£{value:,.2f}", self.c["fg"], False),
                (f"{cur:.1f}%", self.c["fg"], False), (f"{tgt:.1f}%", self.c["muted"], False),
                (f"{drift:+.1f} pp", color, True),
            ]
            for col, (txt, fg, bold) in enumerate(cells):
                self._label(grid, txt, 10, bold, fg=fg).grid(
                    row=r, column=col, sticky="w", padx=6, pady=5)
            self._drift_bar(grid, drift, color).grid(row=r, column=5, padx=6)
            self._label(grid, status, 10, True, fg=color).grid(
                row=r, column=6, sticky="w", padx=6)
        grid.grid_columnconfigure(0, weight=1)

    def _simple_table(self, parent, title, heads, rows, footer=None):
        card = self._card(parent, title)
        card.pack(fill="x", pady=(0, 12))
        grid = tk.Frame(card, bg=self.c["card"])
        grid.pack(fill="x", padx=16, pady=(0, 12))
        for col, h in enumerate(heads):
            self._label(grid, h, 9, fg=self.c["muted"]).grid(
                row=0, column=col, sticky="w", padx=6, pady=(0, 4))
        for r, cells in enumerate(rows, start=1):
            for col, txt in enumerate(cells):
                self._label(grid, txt, 10, col == 0).grid(
                    row=r, column=col, sticky="w", padx=6, pady=4)
        grid.grid_columnconfigure(0, weight=1)
        if footer:
            self._label(card, footer, 10, fg=self.c["muted"]).pack(
                anchor="w", padx=22, pady=(0, 12))

    # ---------------- Calculation ----------------

    def _read_inputs(self):
        try:
            cash = parse_num(self.entry_cash.get())
            invest = parse_num(self.entry_invest.get())
        except ValueError:
            raise ValueError("Cash values must be numbers.")
        if cash < 0 or invest < 0:
            raise ValueError("Cash values can't be negative.")
        if invest > cash:
            raise ValueError(
                f"You're investing £{invest:,.2f} but only have £{cash:,.2f} cash in the account.")

        try:
            equity = round(self.entry_equity.get()) / 100.0
            us = round(self.entry_us.get()) / 100.0
        except ValueError:
            raise ValueError("Target percentages must be numbers.")
        if not (0 <= equity <= 1 and 0 <= us <= 1):
            raise ValueError("Target percentages must be between 0 and 100.")

        class_weight = {
            "US Equity": equity * us,
            "Ex-US Equity": equity * (1 - us),
            "Bond": 1 - equity,
        }

        holdings = []
        for e_name, e_price, e_shares, e_class in self.rows:
            try:
                name = e_name.get().strip()
                price = parse_num(e_price.get())
                shares = int(parse_num(e_shares.get()))
            except ValueError:
                raise ValueError("Holdings table has an invalid number.")
            if not name or price < 0 or shares < 0:
                raise ValueError("Holdings table has an invalid entry.")
            holdings.append({
                "name": name, "price": price, "shares": shares,
                "cls": e_class.get(), "value": price * shares,
            })

        for cls, w in class_weight.items():
            members = [h for h in holdings if h["cls"] == cls]
            if not members and w > 0:
                raise ValueError(f"You have a {w * 100:.0f}% target for {cls} but no fund in that class.")
            for h in members:
                h["weight"] = w / len(members)
        return cash, invest, holdings

    def _plan_buys(self, holdings, invested, invest):
        """Greedy: keep buying the most underweight fund while a share improves the fit."""
        target_total = invested + invest
        for h in holdings:
            h["gap"] = target_total * h["weight"] - h["value"]
        buys = {h["name"]: 0 for h in holdings}
        remaining = invest
        while True:
            options = [
                h for h in holdings
                if 0 < h["price"] <= remaining
                and h["gap"] - buys[h["name"]] * h["price"] >= h["price"] / 2
            ]
            if not options:
                break
            best = max(options, key=lambda h: h["gap"] - buys[h["name"]] * h["price"])
            buys[best["name"]] += 1
            remaining -= best["price"]
        return buys, remaining

    def _split_sections(self, holdings, values):
        """The 70/30 strategy: equities vs bonds, then US vs ex-US within equities."""
        def group(cls_set):
            members = [h for h in holdings if h["cls"] in cls_set]
            return (sum(values[h["name"]] for h in members),
                    sum(h["weight"] for h in members) * 100)

        eq_val, eq_tgt = group({"US Equity", "Ex-US Equity"})
        bond_val, bond_tgt = group({"Bond"})
        us_val, us_tgt = group({"US Equity"})
        xus_val, xus_tgt = group({"Ex-US Equity"})

        def pct(part, whole):
            return part / whole * 100 if whole else 0.0

        total = eq_val + bond_val
        return [
            ("Equities vs Bonds (of invested)", [
                ("Equities", eq_val, pct(eq_val, total), eq_tgt),
                ("Bonds", bond_val, pct(bond_val, total), bond_tgt),
            ]),
            ("US vs Ex-US (of equities)", [
                ("US", us_val, pct(us_val, eq_val), pct(us_tgt, eq_tgt)),
                ("Ex-US", xus_val, pct(xus_val, eq_val), pct(xus_tgt, eq_tgt)),
            ]),
        ]

    def calculate(self):
        try:
            cash, invest, holdings = self._read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return

        self._clear_results()
        self.calculated = True
        invested = sum(h["value"] for h in holdings)
        reserve = cash - invest

        buys, leftover = self._plan_buys(holdings, invested, invest)
        spend = invest - leftover
        reserve_after = reserve + leftover

        self._stat_cards([
            ("Total balance", f"£{invested + cash:,.2f}", self.c["fg"]),
            ("Invested", f"£{invested:,.2f}", self.c["fg"]),
            ("Cash in account", f"£{cash:,.2f}", self.c["fg"]),
            ("Investing now", f"£{spend:,.2f}", self.c["accent"]),
            ("Reserve after", f"£{reserve_after:,.2f}", self.c["muted"]),
        ])

        now_values = {h["name"]: h["value"] for h in holdings}
        self._drift_card(self.right, "Strategy split today",
                         self._split_sections(holdings, now_values))
        self._drift_table(self.right, "Holdings today",
                          [self._row(h, now_values, invested) for h in holdings])

        buy_rows = [
            (h["name"], str(buys[h["name"]]), f"£{h['price']:,.2f}",
             f"£{buys[h['name']] * h['price']:,.2f}")
            for h in holdings if buys[h["name"]] > 0
        ]
        if buy_rows:
            self._simple_table(
                self.right, "Buy plan", ["Fund", "Shares", "Price", "Cost"], buy_rows,
                f"Spend £{spend:,.2f}  ·  left over from this £{invest:,.2f}: £{leftover:,.2f}",
            )
        else:
            card = self._card(self.right, "Buy plan")
            card.pack(fill="x", pady=(0, 12))
            self._label(
                card, "Nothing to buy with this amount – no fund is far enough under target.",
                10, fg=self.c["muted"],
            ).pack(anchor="w", padx=16, pady=(0, 14))

        if buy_rows:
            after_values = {h["name"]: h["value"] + buys[h["name"]] * h["price"] for h in holdings}
            after_total = sum(after_values.values())
            self._drift_card(self.right, "Strategy split after buying",
                             self._split_sections(holdings, after_values))
            self._drift_table(self.right, "Holdings after buying",
                              [self._row(h, after_values, after_total) for h in holdings])

    @staticmethod
    def _row(h, values, total):
        v = values[h["name"]]
        return (h["name"], v, v / total * 100 if total else 0.0, h["weight"] * 100)


if __name__ == "__main__":
    root = tk.Tk()
    ShareAllocator(root)
    root.mainloop()

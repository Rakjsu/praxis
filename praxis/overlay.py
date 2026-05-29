"""Overlay de status — janelinha sempre-no-topo mostrando ON/OFF e a vida lida."""

from __future__ import annotations

import tkinter as tk


class StatusOverlay(tk.Toplevel):
    """Pequena janela sem bordas, sempre no topo e arrastável.

    Mostra o estado do macro (ON/OFF) e a última fração de vida lida pela
    auto-poção. É atualizada externamente via `update_state`.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.85)
        except tk.TclError:
            pass
        self.configure(bg="#11111b")

        self._status = tk.StringVar(value="Praxis: OFF")
        self._health = tk.StringVar(value="Vida: —")
        self._resource = tk.StringVar(value="Recurso: —")
        self._stats = tk.StringVar(value="—")

        frame = tk.Frame(self, bg="#11111b", padx=10, pady=6)
        frame.pack()
        self._status_lbl = tk.Label(
            frame, textvariable=self._status, fg="#9aa0b5", bg="#11111b",
            font=("Segoe UI", 10, "bold"),
        )
        self._status_lbl.pack(anchor="w")
        for var in (self._health, self._resource):
            tk.Label(
                frame, textvariable=var, fg="#cdd6f4", bg="#11111b",
                font=("Segoe UI", 10),
            ).pack(anchor="w")
        tk.Label(
            frame, textvariable=self._stats, fg="#7f849c", bg="#11111b",
            font=("Segoe UI", 8),
        ).pack(anchor="w")

        # Arrastar a janela.
        self._drag = (0, 0)
        for w in (self, frame, self._status_lbl):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        self.geometry("+40+40")

    def _start_drag(self, e: tk.Event) -> None:
        self._drag = (e.x_root - self.winfo_x(), e.y_root - self.winfo_y())

    def _on_drag(self, e: tk.Event) -> None:
        self.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def update_state(
        self,
        running: bool,
        health: float | None = None,
        resource: float | None = None,
        stats: dict | None = None,
    ) -> None:
        self._status.set(f"Praxis: {'ON' if running else 'OFF'}")
        self._status_lbl.config(fg="#a6e3a1" if running else "#9aa0b5")
        self._health.set("Vida: —" if health is None else f"Vida: {health:.0%}")
        self._resource.set("Recurso: —" if resource is None else f"Recurso: {resource:.0%}")
        if stats:
            up = int(stats.get("uptime", 0))
            self._stats.set(
                f"casts {stats.get('casts', 0)} · poções {stats.get('potions', 0)} "
                f"· {up // 60:02d}:{up % 60:02d}"
            )
        else:
            self._stats.set("—")

"""Interface gráfica (Tkinter) do Praxis."""

from __future__ import annotations

import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from . import __app_name__, __version__, config, screen, updater
from .engine import MacroEngine
from .hotkeys import HotkeyManager
from .models import PotionRule, Profile, Settings, Skill
from .overlay import StatusOverlay
from .sender import available_keys

KEY_VALUES = available_keys()


def _virtual_desktop() -> tuple[int, int, int, int]:
    """Retorna (x, y, largura, altura) do desktop virtual (todos os monitores)."""
    try:
        import ctypes

        g = ctypes.windll.user32.GetSystemMetrics
        return g(76), g(77), g(78), g(79)  # X/Y/CX/CY VIRTUALSCREEN
    except Exception:
        return 0, 0, 0, 0


class RegionSelector(tk.Toplevel):
    """Overlay que cobre todos os monitores para selecionar uma região.

    O retângulo é desenhado em coordenadas do canvas (relativas ao canto do
    desktop virtual), mas o resultado é salvo em coordenadas absolutas de tela.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.result: list[int] | None = None

        vx, vy, vw, vh = _virtual_desktop()
        self._offset = (vx, vy)
        if vw > 0 and vh > 0:
            self.overrideredirect(True)
            self.geometry(f"{vw}x{vh}+{vx}+{vy}")
        else:
            self.attributes("-fullscreen", True)

        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.configure(bg="black", cursor="cross")
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._start: tuple[int, int] | None = None
        self._rect = None
        self.canvas.bind("<ButtonPress-1>", self._down)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", self._up)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.canvas.create_text(
            max(1, vw) // 2, 30,
            text="Arraste sobre a barra de vida — ESC para cancelar",
            fill="white", font=("Segoe UI", 14),
        )

    def _to_canvas(self, x_root: int, y_root: int) -> tuple[int, int]:
        return x_root - self._offset[0], y_root - self._offset[1]

    def _down(self, e: tk.Event) -> None:
        self._start = (e.x_root, e.y_root)
        if self._rect:
            self.canvas.delete(self._rect)
        cx, cy = self._to_canvas(e.x_root, e.y_root)
        self._rect = self.canvas.create_rectangle(cx, cy, cx, cy, outline="red", width=2)

    def _move(self, e: tk.Event) -> None:
        if self._start and self._rect:
            cx0, cy0 = self._to_canvas(*self._start)
            cx1, cy1 = self._to_canvas(e.x_root, e.y_root)
            self.canvas.coords(self._rect, cx0, cy0, cx1, cy1)

    def _up(self, e: tk.Event) -> None:
        if not self._start:
            return
        x1, y1 = self._start
        x2, y2 = e.x_root, e.y_root
        self.result = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class SkillRow:
    """Uma linha editável de skill dentro da tabela."""

    def __init__(self, parent: tk.Misc, skill: Skill, on_remove, app: "MacroApp") -> None:
        self.app = app
        self.enabled = tk.BooleanVar(value=skill.enabled)
        self.name = tk.StringVar(value=skill.name)
        self.key = tk.StringVar(value=skill.key)
        self.interval = tk.IntVar(value=skill.interval_ms)
        self.hold = tk.BooleanVar(value=skill.hold)
        # Campos avançados guardados como espelho do modelo (editados no diálogo).
        self.adv = {
            "cooldown_region": list(skill.cooldown_region),
            "ready_color": list(skill.ready_color),
            "ready_tolerance": skill.ready_tolerance,
            "ready_threshold": skill.ready_threshold,
            "condition": skill.condition,
            "condition_pct": skill.condition_pct,
        }

        self.frame = ttk.Frame(parent)
        ttk.Checkbutton(self.frame, variable=self.enabled).grid(row=0, column=0, padx=2)
        ttk.Entry(self.frame, textvariable=self.name, width=13).grid(row=0, column=1, padx=2)
        ttk.Combobox(
            self.frame, textvariable=self.key, values=KEY_VALUES, width=9
        ).grid(row=0, column=2, padx=2)
        ttk.Spinbox(
            self.frame, from_=50, to=600000, increment=50,
            textvariable=self.interval, width=7,
        ).grid(row=0, column=3, padx=2)
        ttk.Checkbutton(self.frame, variable=self.hold).grid(row=0, column=4, padx=2)
        ttk.Button(self.frame, text="⚙", width=3,
                   command=self._open_advanced).grid(row=0, column=5, padx=1)
        ttk.Button(self.frame, text="X", width=3,
                   command=lambda: on_remove(self)).grid(row=0, column=6, padx=1)
        self.frame.pack(fill="x", pady=1)

    def _open_advanced(self) -> None:
        SkillAdvancedDialog(self.app, self)

    def to_skill(self) -> Skill:
        return Skill(
            name=self.name.get().strip() or "Skill",
            key=self.key.get().strip().lower() or "1",
            interval_ms=max(50, int(self.interval.get() or 50)),
            enabled=self.enabled.get(),
            hold=self.hold.get(),
            cooldown_region=list(self.adv["cooldown_region"]),
            ready_color=list(self.adv["ready_color"]),
            ready_tolerance=int(self.adv["ready_tolerance"]),
            ready_threshold=float(self.adv["ready_threshold"]),
            condition=self.adv["condition"],
            condition_pct=int(self.adv["condition_pct"]),
        )

    def destroy(self) -> None:
        self.frame.destroy()


class ComboStepRow:
    """Uma linha editável de passo de combo (tecla + delay)."""

    def __init__(self, parent: tk.Misc, step, on_remove) -> None:
        self.key = tk.StringVar(value=step.key)
        self.delay = tk.IntVar(value=step.delay_ms)
        self.frame = ttk.Frame(parent)
        ttk.Label(self.frame, text="tecla").grid(row=0, column=0, padx=2)
        ttk.Combobox(self.frame, textvariable=self.key, values=KEY_VALUES,
                     width=9).grid(row=0, column=1, padx=2)
        ttk.Label(self.frame, text="delay ms").grid(row=0, column=2, padx=2)
        ttk.Spinbox(self.frame, from_=20, to=60000, increment=20,
                    textvariable=self.delay, width=8).grid(row=0, column=3, padx=2)
        ttk.Button(self.frame, text="X", width=3,
                   command=lambda: on_remove(self)).grid(row=0, column=4, padx=2)
        self.frame.pack(fill="x", pady=1)

    def to_step(self):
        from .models import ComboStep
        return ComboStep(
            key=self.key.get().strip().lower() or "1",
            delay_ms=max(20, int(self.delay.get() or 20)),
        )

    def destroy(self) -> None:
        self.frame.destroy()


class PotionSection:
    """Seção de auto-poção reutilizável (usada para Vida e Recurso)."""

    def __init__(self, parent: tk.Misc, app: "MacroApp", title: str, rule: PotionRule) -> None:
        self.app = app
        self.enabled = tk.BooleanVar(value=rule.enabled)
        self.key = tk.StringVar(value=rule.key)
        self.region_var = tk.StringVar(
            value=",".join(map(str, rule.region)) if any(rule.region) else "(não definida)"
        )
        self.threshold = tk.IntVar(value=int(rule.threshold_pct * 100))
        self.cooldown = tk.IntVar(value=rule.cooldown_ms)
        self.color = tk.StringVar(value=",".join(str(c) for c in rule.color))
        self.tol = tk.IntVar(value=rule.tolerance)

        f = ttk.LabelFrame(parent, text=title)
        f.pack(fill="x", padx=8, pady=4)
        ttk.Checkbutton(f, text="Ativar", variable=self.enabled).grid(
            row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(f, text="Tecla:").grid(row=0, column=1, sticky="e")
        ttk.Combobox(f, textvariable=self.key, values=KEY_VALUES, width=10).grid(
            row=0, column=2, padx=4)

        ttk.Label(f, text="Região:").grid(row=1, column=0, sticky="e", padx=4)
        ttk.Label(f, textvariable=self.region_var).grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Button(f, text="Selecionar região", command=self._select_region).grid(row=1, column=3, padx=4)
        ttk.Button(f, text="Detectar cor", command=self._detect_color).grid(row=1, column=4, padx=4)

        ttk.Label(f, text="Disparar abaixo de (%):").grid(row=2, column=0, columnspan=2, sticky="e")
        ttk.Spinbox(f, from_=1, to=99, textvariable=self.threshold, width=6).grid(
            row=2, column=2, padx=4, sticky="w")
        ttk.Label(f, text="Cooldown (ms):").grid(row=2, column=3, sticky="e")
        ttk.Spinbox(f, from_=100, to=60000, increment=100, textvariable=self.cooldown,
                    width=8).grid(row=2, column=4, padx=4)

        ttk.Label(f, text="Cor (R,G,B):").grid(row=3, column=0, columnspan=2, sticky="e")
        ttk.Entry(f, textvariable=self.color, width=12).grid(row=3, column=2, sticky="w", padx=4)
        ttk.Label(f, text="Tolerância:").grid(row=3, column=3, sticky="e")
        ttk.Spinbox(f, from_=5, to=200, textvariable=self.tol, width=6).grid(
            row=3, column=4, padx=4, sticky="w")
        ttk.Button(f, text="Testar leitura", command=self._test_read).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=4, pady=4)

    def _parse_region(self) -> list[int]:
        raw = self.region_var.get().strip("()[] ")
        try:
            parts = [int(x.strip()) for x in raw.split(",")]
            if len(parts) == 4:
                return parts
        except Exception:
            pass
        return [0, 0, 0, 0]

    def _select_region(self) -> None:
        region = self.app.pick_region()
        if region:
            self.region_var.set(",".join(str(c) for c in region))
            self.app.log(f"Região definida: {region}")

    def _detect_color(self) -> None:
        x1, y1, x2, y2 = self._parse_region()
        if x2 <= x1 or y2 <= y1:
            messagebox.showinfo("Cor", "Defina a região primeiro.")
            return
        try:
            color = screen.sample_color((x1 + x2) // 2, (y1 + y2) // 2)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao ler cor: {exc}")
            return
        self.color.set(",".join(str(c) for c in color))
        self.app.log(f"Cor detectada: {color}")

    def _test_read(self) -> None:
        rule = self.to_potion()
        if not rule.is_configured():
            messagebox.showinfo("Teste", "Ative e defina a região primeiro.")
            return
        try:
            frac = screen.health_fraction(rule.region, rule.color, rule.tolerance)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha na leitura: {exc}")
            return
        self.app.log(f"Leitura atual: {frac:.0%} (dispara abaixo de {rule.threshold_pct:.0%})")

    def to_potion(self) -> PotionRule:
        try:
            color = [int(c) for c in self.color.get().split(",")][:3]
            if len(color) != 3:
                raise ValueError
        except Exception:
            color = [190, 30, 30]
        return PotionRule(
            enabled=self.enabled.get(),
            key=self.key.get().strip().lower() or "q",
            region=self._parse_region(),
            color=color,
            tolerance=int(self.tol.get() or 70),
            threshold_pct=int(self.threshold.get() or 45) / 100,
            cooldown_ms=int(self.cooldown.get() or 2000),
        )

    def apply(self, rule: PotionRule) -> None:
        self.enabled.set(rule.enabled)
        self.key.set(rule.key)
        self.region_var.set(
            ",".join(map(str, rule.region)) if any(rule.region) else "(não definida)"
        )
        self.threshold.set(int(rule.threshold_pct * 100))
        self.cooldown.set(rule.cooldown_ms)
        self.color.set(",".join(str(c) for c in rule.color))
        self.tol.set(rule.tolerance)


class ScrollableFrame(ttk.Frame):
    """Frame com rolagem vertical para acomodar várias seções."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._canvas = tk.Canvas(self, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self.interior = ttk.Frame(self._canvas)
        self.interior.bind(
            "<Configure>",
            lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._win = self._canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self._canvas.bind(
            "<Configure>", lambda e: self._canvas.itemconfig(self._win, width=e.width)
        )
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._canvas.bind("<Enter>", lambda _e: self._bind_wheel())
        self._canvas.bind("<Leave>", lambda _e: self._unbind_wheel())

    def _bind_wheel(self) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self) -> None:
        self._canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, e: tk.Event) -> None:
        self._canvas.yview_scroll(int(-e.delta / 120), "units")


CONDITIONS = ["none", "health_below", "health_above", "resource_below", "resource_above"]
CONDITION_LABELS = {
    "none": "(nenhuma)",
    "health_below": "vida abaixo de %",
    "health_above": "vida acima de %",
    "resource_below": "recurso abaixo de %",
    "resource_above": "recurso acima de %",
}


class SkillAdvancedDialog(tk.Toplevel):
    """Configura cooldown por ícone e cast condicional de uma skill."""

    def __init__(self, app: "MacroApp", row: "SkillRow") -> None:
        super().__init__(app)
        self.app = app
        self.row = row
        self.title(f"Avançado — {row.name.get() or 'Skill'}")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()

        adv = row.adv
        self.region_var = tk.StringVar(
            value=",".join(map(str, adv["cooldown_region"]))
            if any(adv["cooldown_region"]) else "(não definida)"
        )
        self.color = tk.StringVar(value=",".join(str(c) for c in adv["ready_color"]))
        self.tol = tk.IntVar(value=adv["ready_tolerance"])
        self.threshold = tk.IntVar(value=int(adv["ready_threshold"] * 100))
        self._cond_label = tk.StringVar(value=CONDITION_LABELS[adv["condition"]])
        self.cond_pct = tk.IntVar(value=adv["condition_pct"])

        pad = {"padx": 8, "pady": 3}
        cd = ttk.LabelFrame(self, text="Detecção de cooldown (ícone)")
        cd.pack(fill="x", **pad)
        ttk.Label(cd, text="Região:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        ttk.Label(cd, textvariable=self.region_var).grid(row=0, column=1, columnspan=2, sticky="w")
        ttk.Button(cd, text="Selecionar", command=self._select_region).grid(row=0, column=3, padx=4)
        ttk.Button(cd, text="Detectar cor", command=self._detect_color).grid(row=0, column=4, padx=4)
        ttk.Label(cd, text="Cor pronta (R,G,B):").grid(row=1, column=0, columnspan=2, sticky="e")
        ttk.Entry(cd, textvariable=self.color, width=12).grid(row=1, column=2, sticky="w", padx=4)
        ttk.Label(cd, text="Tolerância:").grid(row=1, column=3, sticky="e")
        ttk.Spinbox(cd, from_=5, to=200, textvariable=self.tol, width=6).grid(row=1, column=4, padx=4)
        ttk.Label(cd, text="Pronta acima de (%):").grid(row=2, column=0, columnspan=2, sticky="e")
        ttk.Spinbox(cd, from_=1, to=99, textvariable=self.threshold, width=6).grid(
            row=2, column=2, sticky="w", padx=4)

        co = ttk.LabelFrame(self, text="Cast condicional")
        co.pack(fill="x", **pad)
        ttk.Label(co, text="Condição:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        ttk.Combobox(co, textvariable=self._cond_label, state="readonly",
                     values=[CONDITION_LABELS[c] for c in CONDITIONS], width=22).grid(
            row=0, column=1, columnspan=2, sticky="w", padx=4)
        ttk.Label(co, text="Limite (%):").grid(row=0, column=3, sticky="e")
        ttk.Spinbox(co, from_=1, to=99, textvariable=self.cond_pct, width=6).grid(row=0, column=4, padx=4)

        btns = ttk.Frame(self)
        btns.pack(pady=8)
        ttk.Button(btns, text="OK", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=4)

    def _parse_region(self) -> list[int]:
        raw = self.region_var.get().strip("()[] ")
        try:
            parts = [int(x.strip()) for x in raw.split(",")]
            if len(parts) == 4:
                return parts
        except Exception:
            pass
        return [0, 0, 0, 0]

    def _select_region(self) -> None:
        region = self.app.pick_region()
        if region:
            self.region_var.set(",".join(str(c) for c in region))

    def _detect_color(self) -> None:
        x1, y1, x2, y2 = self._parse_region()
        if x2 <= x1 or y2 <= y1:
            messagebox.showinfo("Cor", "Defina a região primeiro.")
            return
        try:
            color = screen.sample_color((x1 + x2) // 2, (y1 + y2) // 2)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao ler cor: {exc}")
            return
        self.color.set(",".join(str(c) for c in color))

    def _save(self) -> None:
        try:
            color = [int(c) for c in self.color.get().split(",")][:3]
            if len(color) != 3:
                raise ValueError
        except Exception:
            color = [200, 200, 200]
        label_to_cond = {v: k for k, v in CONDITION_LABELS.items()}
        self.row.adv = {
            "cooldown_region": self._parse_region(),
            "ready_color": color,
            "ready_tolerance": int(self.tol.get() or 70),
            "ready_threshold": int(self.threshold.get() or 50) / 100,
            "condition": label_to_cond.get(self._cond_label.get(), "none"),
            "condition_pct": int(self.cond_pct.get() or 50),
        }
        self.destroy()


class RegionPreview(tk.Toplevel):
    """Overlay temporário que desenha retângulos das regiões configuradas."""

    def __init__(self, master: tk.Misc, regions: list[tuple[str, list[int]]]) -> None:
        super().__init__(master)
        vx, vy, vw, vh = _virtual_desktop()
        if vw > 0 and vh > 0:
            self.overrideredirect(True)
            self.geometry(f"{vw}x{vh}+{vx}+{vy}")
        else:
            self.attributes("-fullscreen", True)
            vx = vy = 0
        self.attributes("-alpha", 0.35)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        colors = {"vida": "#ff5555", "recurso": "#5599ff"}
        for label, region in regions:
            x1, y1, x2, y2 = region
            if x2 <= x1 or y2 <= y1:
                continue
            col = colors.get(label, "#f9e2af")
            canvas.create_rectangle(x1 - vx, y1 - vy, x2 - vx, y2 - vy, outline=col, width=3)
            canvas.create_text(x1 - vx + 4, y1 - vy - 10, text=label, fill=col,
                               anchor="w", font=("Segoe UI", 10, "bold"))
        self.after(2500, self.destroy)


class OptionsDialog(tk.Toplevel):
    """Janela de opções globais (Settings)."""

    def __init__(self, app: "MacroApp") -> None:
        super().__init__(app)
        self.app = app
        self.title("Opções")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()

        s = app.settings
        self.start_minimized = tk.BooleanVar(value=s.start_minimized)
        self.overlay_enabled = tk.BooleanVar(value=s.overlay_enabled)
        self.log_to_file = tk.BooleanVar(value=s.log_to_file)
        self.minimize_to_tray = tk.BooleanVar(value=s.minimize_to_tray)
        self.panic_key = tk.StringVar(value=s.panic_key)
        self.cycle_profile_key = tk.StringVar(value=s.cycle_profile_key)

        pad = {"padx": 10, "pady": 4}
        ttk.Checkbutton(self, text="Iniciar minimizado",
                        variable=self.start_minimized).grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(self, text="Mostrar overlay de status",
                        variable=self.overlay_enabled).grid(row=1, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(self, text="Salvar log em arquivo (praxis.log)",
                        variable=self.log_to_file).grid(row=2, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(self, text="Minimizar para a bandeja (system tray)",
                        variable=self.minimize_to_tray).grid(row=3, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(self, text="Tecla de pânico (para tudo):").grid(row=4, column=0, sticky="w", **pad)
        ttk.Combobox(self, textvariable=self.panic_key, values=KEY_VALUES,
                     width=10).grid(row=4, column=1, sticky="w", **pad)
        ttk.Label(self, text="Tecla trocar perfil:").grid(row=5, column=0, sticky="w", **pad)
        ttk.Combobox(self, textvariable=self.cycle_profile_key, values=[""] + KEY_VALUES,
                     width=10).grid(row=5, column=1, sticky="w", **pad)

        btns = ttk.Frame(self)
        btns.grid(row=6, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Salvar", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=4)

    def _save(self) -> None:
        self.app.settings = Settings(
            start_minimized=self.start_minimized.get(),
            overlay_enabled=self.overlay_enabled.get(),
            panic_key=self.panic_key.get().strip().lower() or "f9",
            log_to_file=self.log_to_file.get(),
            minimize_to_tray=self.minimize_to_tray.get(),
            cycle_profile_key=self.cycle_profile_key.get().strip().lower(),
        )
        config.save_settings(self.app.settings)
        self.app._apply_settings()
        self.app.log("Opções salvas.")
        self.destroy()


class MacroApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{__app_name__} v{__version__}")
        self.geometry("620x760")
        self.minsize(560, 660)

        self.engine = MacroEngine(log=self.log)
        self.hotkeys = HotkeyManager()
        self.panic_hotkeys = HotkeyManager()
        self.profile_hotkeys = HotkeyManager()
        self.skill_rows: list[SkillRow] = []
        self.combo_rows: list[ComboStepRow] = []
        self._pending_update: updater.UpdateInfo | None = None
        self.settings = config.load_settings()
        self.overlay: StatusOverlay | None = None
        self.tray = None

        self._build()
        self._load_initial_profile()
        self._apply_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._refresh_status)
        self.after(1500, self._check_update_async)
        if self.settings.start_minimized:
            self.iconify()

    # --- construção da UI --------------------------------------------------

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # --- área inferior fixa (controle + log), ancorada embaixo ---
        logf = ttk.LabelFrame(self, text="Log")
        logf.pack(side="bottom", fill="x", **pad)
        self.log_text = tk.Text(logf, height=7, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

        self.update_bar = ttk.Frame(self)
        self.update_lbl = ttk.Label(self.update_bar, foreground="#7a3cff")
        self.update_lbl.pack(side="left", padx=4)
        self.update_btn = ttk.Button(self.update_bar, text="Atualizar agora",
                                     command=self._apply_update)
        self.update_btn.pack(side="left", padx=4)

        ctrl = ttk.Frame(self)
        ctrl.pack(side="bottom", fill="x", **pad)
        self.toggle_btn = ttk.Button(ctrl, text="▶ Iniciar (OFF)", command=self._toggle)
        self.toggle_btn.pack(side="left")
        self.status_lbl = ttk.Label(ctrl, text="parado", foreground="gray")
        self.status_lbl.pack(side="left", padx=10)
        ttk.Button(ctrl, text="Preview regiões",
                   command=self._preview_regions).pack(side="left", padx=4)
        ttk.Button(ctrl, text="Verificar atualizações",
                   command=self._check_update_async).pack(side="right")

        # --- corpo rolável ---
        body = ScrollableFrame(self)
        body.pack(side="top", fill="both", expand=True)
        root = body.interior

        # Barra de perfis
        top = ttk.LabelFrame(root, text="Perfil")
        top.pack(fill="x", **pad)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            top, textvariable=self.profile_var, state="readonly", width=24
        )
        self.profile_combo.grid(row=0, column=0, padx=4, pady=6)
        self.profile_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_pick_profile())
        ttk.Button(top, text="Novo", command=self._new_profile).grid(row=0, column=1, padx=2)
        ttk.Button(top, text="Salvar", command=self._save_profile).grid(row=0, column=2, padx=2)
        ttk.Button(top, text="Excluir", command=self._delete_profile).grid(row=0, column=3, padx=2)
        ttk.Button(top, text="Opções", command=self._open_options).grid(row=0, column=4, padx=2)

        # Nome + hotkey + janela-alvo + jitter
        meta = ttk.Frame(root)
        meta.pack(fill="x", **pad)
        ttk.Label(meta, text="Nome:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.name_var, width=24).grid(row=0, column=1, padx=4)
        ttk.Label(meta, text="Hotkey:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.hotkey_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.hotkey_var, width=6).grid(row=0, column=3, padx=4)
        ttk.Button(meta, text="Aplicar", command=self._apply_hotkey).grid(row=0, column=4)
        ttk.Label(meta, text="Janela-alvo:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.target_window_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.target_window_var, width=24).grid(
            row=1, column=1, padx=4, pady=(4, 0))
        ttk.Label(meta, text="Jitter %:").grid(row=1, column=2, sticky="w", padx=(12, 0))
        self.jitter_var = tk.IntVar(value=0)
        ttk.Spinbox(meta, from_=0, to=90, textvariable=self.jitter_var, width=6).grid(
            row=1, column=3, padx=4, pady=(4, 0))

        # Skills
        sk = ttk.LabelFrame(root, text="Rotação de Skills")
        sk.pack(fill="both", **pad)
        header = ttk.Frame(sk)
        header.pack(fill="x")
        for i, txt in enumerate(["On", "Nome", "Tecla", "ms", "Hold", "Avç"]):
            ttk.Label(header, text=txt, width=[4, 13, 10, 8, 5, 4][i],
                      anchor="w").grid(row=0, column=i, padx=2)
        self.skills_container = ttk.Frame(sk)
        self.skills_container.pack(fill="both", expand=True)
        ttk.Button(sk, text="+ Adicionar skill",
                   command=lambda: self._add_skill_row(Skill())).pack(anchor="w", pady=4)

        # Combo / sequência
        cb = ttk.LabelFrame(root, text="Combo / Sequência")
        cb.pack(fill="x", **pad)
        opts = ttk.Frame(cb)
        opts.pack(fill="x")
        self.combo_enabled = tk.BooleanVar()
        ttk.Checkbutton(opts, text="Ativar", variable=self.combo_enabled).pack(side="left", padx=4)
        self.combo_loop = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Loop", variable=self.combo_loop).pack(side="left", padx=4)
        self.combo_container = ttk.Frame(cb)
        self.combo_container.pack(fill="both", expand=True)
        ttk.Button(cb, text="+ Adicionar passo",
                   command=lambda: self._add_combo_row(None)).pack(anchor="w", pady=4)

        # Auto-poções (vida e recurso) — seções reutilizáveis
        self.potion_section = PotionSection(root, self, "Auto-Poção (vida)", PotionRule())
        self.resource_section = PotionSection(
            root, self, "Auto-Poção (recurso/mana)", PotionRule(key="w", color=[40, 80, 200])
        )

    # --- region picker (compartilhado pelas seções de poção) --------------

    def pick_region(self) -> list[int] | None:
        self.withdraw()
        self.update()
        time.sleep(0.2)
        sel = RegionSelector(self)
        self.wait_window(sel)
        self.deiconify()
        return sel.result

    # --- skills ------------------------------------------------------------

    def _add_skill_row(self, skill: Skill) -> None:
        row = SkillRow(self.skills_container, skill, self._remove_skill_row, self)
        self.skill_rows.append(row)

    def _remove_skill_row(self, row: SkillRow) -> None:
        row.destroy()
        self.skill_rows.remove(row)

    def _add_combo_row(self, step) -> None:
        from .models import ComboStep
        row = ComboStepRow(self.combo_container, step or ComboStep(), self._remove_combo_row)
        self.combo_rows.append(row)

    def _remove_combo_row(self, row) -> None:
        row.destroy()
        self.combo_rows.remove(row)

    def _clear_combo(self) -> None:
        for row in list(self.combo_rows):
            row.destroy()
        self.combo_rows.clear()

    def _clear_skills(self) -> None:
        for row in list(self.skill_rows):
            row.destroy()
        self.skill_rows.clear()

    # --- perfis ------------------------------------------------------------

    def _refresh_profile_list(self, select: str | None = None) -> None:
        names = config.list_profiles()
        self.profile_combo["values"] = names
        if select and select in names:
            self.profile_var.set(select)
        elif names and not self.profile_var.get():
            self.profile_var.set(names[0])

    def _load_initial_profile(self) -> None:
        self._refresh_profile_list()
        names = config.list_profiles()
        if names:
            self.profile_var.set(names[0])
            self._on_pick_profile()
        else:
            self._apply_profile_to_form(Profile(name="Diablo", toggle_hotkey="f8"))

    def _on_pick_profile(self) -> None:
        stem = self.profile_var.get()
        if not stem:
            return
        try:
            profile = config.load_profile(stem)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao carregar perfil: {exc}")
            return
        self._apply_profile_to_form(profile)
        self._apply_hotkey()

    def _apply_profile_to_form(self, profile: Profile) -> None:
        self.name_var.set(profile.name)
        self.hotkey_var.set(profile.toggle_hotkey)
        self.target_window_var.set(profile.target_window)
        self.jitter_var.set(profile.jitter_pct)
        self._clear_skills()
        for skill in profile.skills:
            self._add_skill_row(skill)
        if not profile.skills:
            self._add_skill_row(Skill())
        self._clear_combo()
        for step in profile.combo.steps:
            self._add_combo_row(step)
        self.combo_enabled.set(profile.combo.enabled)
        self.combo_loop.set(profile.combo.loop)
        self.potion_section.apply(profile.potion)
        self.resource_section.apply(profile.resource)

    def _form_to_profile(self) -> Profile:
        from .models import Combo
        return Profile(
            name=self.name_var.get().strip() or "Perfil",
            toggle_hotkey=self.hotkey_var.get().strip().lower() or "f8",
            skills=[r.to_skill() for r in self.skill_rows],
            potion=self.potion_section.to_potion(),
            resource=self.resource_section.to_potion(),
            combo=Combo(
                enabled=self.combo_enabled.get(),
                loop=self.combo_loop.get(),
                steps=[r.to_step() for r in self.combo_rows],
            ),
            target_window=self.target_window_var.get().strip(),
            jitter_pct=int(self.jitter_var.get() or 0),
        )

    def _new_profile(self) -> None:
        self.profile_var.set("")
        self._apply_profile_to_form(Profile(name="Novo Perfil", toggle_hotkey="f8"))

    def _save_profile(self) -> None:
        profile = self._form_to_profile()
        path = config.save_profile(profile)
        self._refresh_profile_list(select=path.stem)
        self.engine.set_profile(profile)
        self.log(f"Perfil salvo: {path.name}")

    def _delete_profile(self) -> None:
        stem = self.profile_var.get()
        if not stem:
            return
        if messagebox.askyesno("Excluir", f"Excluir o perfil '{stem}'?"):
            config.delete_profile(stem)
            self.profile_var.set("")
            self._refresh_profile_list()
            self.log(f"Perfil excluído: {stem}")

    # --- hotkey + controle -------------------------------------------------

    def _apply_hotkey(self) -> None:
        hk = self.hotkey_var.get().strip().lower() or "f8"
        if not self.hotkeys.available:
            self.log("[!] lib 'keyboard' indisponível — hotkey global desativada")
            return
        ok = self.hotkeys.register(hk, self._hotkey_fired)
        self.log(f"Hotkey '{hk}' {'registrada' if ok else 'FALHOU'}")

    def _hotkey_fired(self) -> None:
        # Chamado pela thread do `keyboard`; volta para a thread da UI.
        self.after(0, self._toggle)

    def _toggle(self) -> None:
        profile = self._form_to_profile()
        self.engine.toggle(profile)
        self._refresh_status()

    def _refresh_status(self) -> None:
        running = self.engine.running
        if running:
            self.toggle_btn.config(text="■ Parar (ON)")
            self.status_lbl.config(text="RODANDO", foreground="green")
        else:
            self.toggle_btn.config(text="▶ Iniciar (OFF)")
            self.status_lbl.config(text="parado", foreground="gray")
        if self.overlay is not None:
            stats = {
                "casts": self.engine.casts,
                "potions": self.engine.potions_used,
                "uptime": self.engine.uptime(),
            }
            self.overlay.update_state(
                running, self.engine.last_health, self.engine.last_resource, stats
            )
        self.after(400, self._refresh_status)

    # --- opções + pânico ---------------------------------------------------

    def _apply_settings(self) -> None:
        """Aplica as configurações: overlay e tecla de pânico."""
        # Overlay
        if self.settings.overlay_enabled and self.overlay is None:
            self.overlay = StatusOverlay(self)
        elif not self.settings.overlay_enabled and self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None

        # Tecla de pânico (precisa diferir da hotkey de liga/desliga)
        panic = self.settings.panic_key.strip().lower()
        toggle = self.hotkey_var.get().strip().lower() if hasattr(self, "hotkey_var") else ""
        if panic and panic != toggle and self.panic_hotkeys.available:
            ok = self.panic_hotkeys.register(panic, self._panic_fired)
            self.log(f"Tecla de pânico '{panic}' {'registrada' if ok else 'FALHOU'}")
        else:
            self.panic_hotkeys.unregister()
            if panic and panic == toggle:
                self.log("[!] tecla de pânico igual à de liga/desliga — ignorada")

        # Tecla de trocar perfil (precisa diferir de toggle e pânico)
        cycle = self.settings.cycle_profile_key.strip().lower()
        if cycle and cycle not in (toggle, panic) and self.profile_hotkeys.available:
            ok = self.profile_hotkeys.register(cycle, lambda: self.after(0, self._cycle_profile))
            self.log(f"Tecla trocar perfil '{cycle}' {'registrada' if ok else 'FALHOU'}")
        else:
            self.profile_hotkeys.unregister()
            if cycle and cycle in (toggle, panic):
                self.log("[!] tecla de trocar perfil conflita com outra — ignorada")

        # System tray
        self._apply_tray()

    def _apply_tray(self) -> None:
        if self.settings.minimize_to_tray and self.tray is None:
            try:
                from .tray import TrayController
                self.tray = TrayController(
                    on_show=lambda: self.after(0, self._restore_window),
                    on_toggle=lambda: self.after(0, self._toggle),
                    on_quit=lambda: self.after(0, self._quit_from_tray),
                )
                self.tray.start()
            except Exception as exc:
                self.tray = None
                self.log(f"[!] system tray indisponível: {exc}")
        elif not self.settings.minimize_to_tray and self.tray is not None:
            self.tray.stop()
            self.tray = None

    def _restore_window(self) -> None:
        self.deiconify()
        self.lift()

    def _quit_from_tray(self) -> None:
        self._closing_to_tray = False
        self._on_close()

    def _hide_to_tray(self) -> None:
        self.withdraw()
        self.log("Minimizado para a bandeja.")

    def _cycle_profile(self) -> None:
        names = config.list_profiles()
        if not names:
            return
        cur = self.profile_var.get()
        idx = names.index(cur) + 1 if cur in names else 0
        self.profile_var.set(names[idx % len(names)])
        self._on_pick_profile()
        self.log(f"Perfil -> {self.profile_var.get()}")

    def _preview_regions(self) -> None:
        prof = self._form_to_profile()
        regions = [("vida", prof.potion.region), ("recurso", prof.resource.region)]
        for sk in prof.skills:
            if sk.has_cooldown_check():
                regions.append((f"cd:{sk.name}", sk.cooldown_region))
        RegionPreview(self, regions)

    def _panic_fired(self) -> None:
        self.after(0, self._panic)

    def _panic(self) -> None:
        self.engine.stop()
        self._refresh_status()
        self.log("[PÂNICO] tudo parado")

    def _open_options(self) -> None:
        OptionsDialog(self)

    # --- auto-update -------------------------------------------------------

    def _check_update_async(self) -> None:
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self) -> None:
        info = updater.check_for_update()
        self.after(0, lambda: self._on_update_result(info))

    def _on_update_result(self, info: "updater.UpdateInfo | None") -> None:
        if info is None:
            self.log("Você está na versão mais recente.")
            return
        self._pending_update = info
        self.update_lbl.config(text=f"Nova versão disponível: v{info.version}")
        self.update_bar.pack(fill="x", padx=8, pady=(0, 4))
        self.log(f"Atualização encontrada: v{info.version}")

    def _apply_update(self) -> None:
        info = self._pending_update
        if not info:
            return
        if not info.download_url:
            webbrowser.open(info.release_url)
            return
        if not messagebox.askyesno(
            "Atualizar",
            f"Baixar e instalar a v{info.version} agora?\nO Praxis será fechado.",
        ):
            return
        self.log("Baixando atualização...")
        if updater.download_and_run(info.download_url, info.sha256_url):
            self._on_close()
        else:
            messagebox.showerror(
                "Atualização",
                "Falha ao baixar ou verificar a integridade. Abrindo a página do release.",
            )
            webbrowser.open(info.release_url)

    # --- log + ciclo de vida ----------------------------------------------

    def log(self, msg: str) -> None:
        line = time.strftime("%H:%M:%S ") + msg

        def _append() -> None:
            self.log_text.config(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _append)

        if getattr(self, "settings", None) and self.settings.log_to_file:
            try:
                path = config.PROFILES_DIR.parent / "praxis.log"
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(time.strftime("%Y-%m-%d ") + line + "\n")
            except Exception:
                pass

    def _on_close(self) -> None:
        # Se "minimizar para bandeja" estiver ativo e o tray disponível, esconde
        # em vez de fechar (a saída definitiva vem pelo menu do tray).
        if self.settings.minimize_to_tray and self.tray is not None:
            self._hide_to_tray()
            return
        self.engine.stop()
        self.hotkeys.unregister()
        self.panic_hotkeys.unregister()
        self.profile_hotkeys.unregister()
        if self.overlay is not None:
            self.overlay.destroy()
        if self.tray is not None:
            self.tray.stop()
        self.destroy()


def run() -> None:
    config.seed_defaults()
    app = MacroApp()
    app.mainloop()

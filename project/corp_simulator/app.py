from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask, render_template, request, redirect, url_for, flash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "events.json"

DEFAULT_STATE: Dict[str, Any] = {
    "company": "NovaCorp",
    "day": 1,
    "cash": 10000,
    "staff": 4,
    "reputation": 18,
    "product": 12,
    "technology": 8,
    "risk": 6,
    "level": 1,
    "last_action": "Компания зарегистрирована и готова к развитию."
}

ACTIONS: Dict[str, Dict[str, Any]] = {
    "hire": {
        "name": "Нанять сотрудников",
        "cash": -1200,
        "staff": 2,
        "reputation": 1,
        "risk": 1,
        "message": "Отдел кадров нанял двух специалистов. Производственные возможности выросли."
    },
    "marketing": {
        "name": "Запустить рекламу",
        "cash": -900,
        "reputation": 5,
        "risk": 1,
        "message": "Маркетинговая кампания повысила узнаваемость бренда."
    },
    "product": {
        "name": "Улучшить продукт",
        "cash": -1500,
        "product": 6,
        "technology": 1,
        "message": "Команда разработки выпустила обновление продукта."
    },
    "research": {
        "name": "Исследовать технологию",
        "cash": -1800,
        "technology": 7,
        "risk": -1,
        "message": "Исследовательский отдел внедрил новую технологию и снизил операционные риски."
    },
    "sale": {
        "name": "Провести продажи",
        "cash_formula": "sale",
        "reputation": 1,
        "message": "Отдел продаж заключил серию контрактов с клиентами."
    },
    "audit": {
        "name": "Провести аудит",
        "cash": -700,
        "risk": -5,
        "reputation": 2,
        "message": "Внутренний аудит выявил слабые места и улучшил устойчивость корпорации."
    }
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "practice-secret-key-change-in-production"
    DATA_DIR.mkdir(exist_ok=True)
    ensure_files()

    @app.route("/")
    def index():
        state = load_state()
        events = load_events()[-5:]
        metrics = calculate_metrics(state)
        return render_template("index.html", state=state, events=list(reversed(events)), metrics=metrics, actions=ACTIONS)

    @app.route("/action", methods=["POST"])
    def action():
        action_key = request.form.get("action")
        state = load_state()
        if action_key not in ACTIONS:
            flash("Неизвестное действие.", "error")
            return redirect(url_for("index"))

        action_info = ACTIONS[action_key]
        if action_info.get("cash", 0) < 0 and state["cash"] + action_info["cash"] < 0:
            flash("Недостаточно средств для выполнения действия.", "error")
            return redirect(url_for("index"))

        before = state.copy()
        apply_action(state, action_key)
        save_state(state)
        write_event(action_key, action_info["name"], before, state)
        flash(action_info["message"], "success")
        return redirect(url_for("index"))

    @app.route("/strategy", methods=["GET", "POST"])
    def strategy():
        state = load_state()
        if request.method == "POST":
            name = request.form.get("company", "").strip()
            if not name:
                flash("Название корпорации не может быть пустым.", "error")
            else:
                old_name = state["company"]
                state["company"] = name[:40]
                state["last_action"] = f"Корпорация переименована: {old_name} -> {state['company']}."
                save_state(state)
                write_custom_event("Изменение стратегии", state["last_action"])
                flash("Стратегия обновлена.", "success")
                return redirect(url_for("strategy"))
        return render_template("strategy.html", state=state, metrics=calculate_metrics(state))

    @app.route("/admin-panel")
    def admin_panel():
        state = load_state()
        events = list(reversed(load_events()))
        return render_template("admin.html", state=state, events=events, metrics=calculate_metrics(state))

    @app.route("/reset", methods=["POST"])
    def reset():
        save_state(DEFAULT_STATE.copy())
        save_events([])
        write_custom_event("Сброс", "Состояние симулятора возвращено к исходным значениям.")
        flash("Симулятор сброшен до стартового состояния.", "success")
        return redirect(url_for("index"))

    return app


def ensure_files() -> None:
    if not STATE_FILE.exists():
        save_state(DEFAULT_STATE.copy())
    if not LOG_FILE.exists():
        save_events([])


def load_state() -> Dict[str, Any]:
    with STATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def load_events() -> List[Dict[str, Any]]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_events(events: List[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with LOG_FILE.open("w", encoding="utf-8") as file:
        json.dump(events, file, ensure_ascii=False, indent=2)


def calculate_metrics(state: Dict[str, Any]) -> Dict[str, Any]:
    market_power = state["reputation"] * 2 + state["product"] * 3 + state["technology"] * 2 + state["staff"]
    stability = max(0, 100 - state["risk"] * 6)
    level = max(1, market_power // 30)
    state["level"] = int(level)
    return {
        "market_power": int(market_power),
        "stability": int(stability),
        "efficiency": int((state["product"] + state["technology"] + state["staff"]) / 3),
        "valuation": int(state["cash"] + market_power * 170)
    }


def apply_action(state: Dict[str, Any], action_key: str) -> None:
    action_info = ACTIONS[action_key]
    state["day"] += 1
    for key in ["cash", "staff", "reputation", "product", "technology", "risk"]:
        if key in action_info:
            state[key] += action_info[key]
    if action_info.get("cash_formula") == "sale":
        revenue = 600 + state["product"] * 90 + state["reputation"] * 65 + state["staff"] * 80
        state["cash"] += revenue
        state["last_action"] = f"Продажи принесли {revenue} ₽ виртуальной выручки."
    else:
        state["last_action"] = action_info["message"]
    state["cash"] = max(0, state["cash"])
    state["risk"] = min(20, max(0, state["risk"]))
    state["reputation"] = max(0, state["reputation"])
    state["product"] = max(0, state["product"])
    state["technology"] = max(0, state["technology"])


def write_event(action_key: str, action_name: str, before: Dict[str, Any], after: Dict[str, Any]) -> None:
    events = load_events()
    events.append({
        "time": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "action": action_name,
        "description": after["last_action"],
        "cash_delta": after["cash"] - before["cash"],
        "day": after["day"]
    })
    save_events(events[-100:])


def write_custom_event(action: str, description: str) -> None:
    events = load_events()
    events.append({
        "time": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "action": action,
        "description": description,
        "cash_delta": 0,
        "day": load_state().get("day", 1)
    })
    save_events(events[-100:])


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

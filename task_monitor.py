import os
import json
import time

USERPROFILE = os.environ.get("USERPROFILE", os.path.expanduser("~"))
BRAIN_DIR = os.path.join(USERPROFILE, ".gemini", "antigravity", "brain")

def get_current_task_status():
    """
    Checks if a real Antigravity coding task/session is actively running.
    Returns: (is_running: bool, title: str, summary: str)
    """
    try:
        if not os.path.exists(BRAIN_DIR):
            return False, "", ""

        folders = [
            os.path.join(BRAIN_DIR, d)
            for d in os.listdir(BRAIN_DIR)
            if os.path.isdir(os.path.join(BRAIN_DIR, d)) and d != "tempmediaStorage"
        ]
        if not folders:
            return False, "", ""

        latest_folder = max(folders, key=os.path.getmtime)
        t_file = os.path.join(latest_folder, ".system_generated", "logs", "transcript.jsonl")
        if not os.path.exists(t_file):
            return False, "", ""

        mtime = os.path.getmtime(t_file)
        age = time.time() - mtime

        # If transcript was modified > 25s ago, definitely idle
        if age > 25.0:
            return False, "", ""

        with open(t_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines:
            return False, "", ""

        last_step = {}
        try:
            last_step = json.loads(lines[-1])
        except Exception:
            pass

        step_type = last_step.get("type")
        has_tools = bool(last_step.get("tool_calls"))

        # If the turn has ended with a final response (no tool calls) or checkpoint
        if step_type in ("PLANNER_RESPONSE", "CHECKPOINT") and not has_tools:
            return False, "", ""

        # Extract last user prompt
        last_user_prompt = ""
        for line in reversed(lines):
            try:
                obj = json.loads(line)
                if obj.get("type") == "USER_INPUT":
                    content = obj.get("content", "")
                    if content and not content.startswith("<SYSTEM_MESSAGE>"):
                        last_user_prompt = content
                        break
            except Exception:
                continue

        summary = last_user_prompt.strip()
        if "<USER_REQUEST>" in summary:
            parts = summary.split("<USER_REQUEST>")
            if len(parts) > 1:
                summary = parts[1].split("</USER_REQUEST>")[0].strip()

        # Clean up tags and extra whitespace
        summary = summary.replace("\n", " ").strip()
        while "  " in summary:
            summary = summary.replace("  ", " ")

        if len(summary) > 95:
            summary = summary[:92] + "..."

        session_id = os.path.basename(latest_folder)[:8]
        title = f"Antigravity 2.0 • Active ({session_id})"
        return True, title, summary or "Active Antigravity task in progress..."

    except Exception:
        return False, "", ""

if __name__ == "__main__":
    is_active, title, summary = get_current_task_status()
    print("Active:", is_active)
    print("Title:", title)
    print("Summary:", summary)

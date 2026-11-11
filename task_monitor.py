import os
import glob
import json
import time

USERPROFILE = os.environ.get("USERPROFILE", os.path.expanduser("~"))
BRAIN_DIR = os.path.join(USERPROFILE, ".gemini", "antigravity", "brain")

def get_all_active_tasks():
    """
    Scans all recent Antigravity transcripts across all conversations and
    determines which sessions are actively running, thinking, or executing tools.
    
    Returns:
        List of dicts: [
            {
                "id": conversation_id,
                "short_id": short_id,
                "title": title_with_status,
                "summary": cleaned_prompt_summary,
                "state": "Thinking..." | "Executing tool..." | "Processing results...",
                "age": seconds_since_last_event
            },
            ...
        ]
    """
    if not os.path.exists(BRAIN_DIR):
        return []

    pattern = os.path.join(BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl")
    files = glob.glob(pattern)
    if not files:
        return []

    # Sort transcripts by ACTUAL file modification time (newest first)
    files.sort(key=os.path.getmtime, reverse=True)

    now = time.time()
    active_tasks = []

    for f in files:
        mtime = os.path.getmtime(f)
        age = now - mtime

        # If transcript has had no activity for more than 20 minutes, skip
        if age > 1200.0:
            continue

        conv_dir = os.path.dirname(os.path.dirname(os.path.dirname(f)))
        conv_id = os.path.basename(conv_dir)
        if conv_id == "tempmediaStorage":
            continue

        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                lines = [l.strip() for l in fp if l.strip()]
        except Exception:
            continue

        if not lines:
            continue

        last_step = {}
        try:
            last_step = json.loads(lines[-1])
        except Exception:
            continue

        step_type = last_step.get("type")
        has_tools = bool(last_step.get("tool_calls"))

        # Determine if this session turn is actively working
        is_running = False
        task_state = "Working..."

        if step_type == "USER_INPUT":
            is_running = True
            task_state = "Thinking & planning..."
        elif step_type == "PLANNER_RESPONSE" and has_tools:
            is_running = True
            task_state = "Executing tool..."
        elif step_type == "GENERIC":
            is_running = True
            task_state = "Processing results..."
        elif step_type in ("PLANNER_RESPONSE", "CHECKPOINT") and not has_tools:
            # Turn concluded with final message
            is_running = False

        # If more than 3 minutes of total silence on a turn, consider stalled/idle
        if age > 180.0:
            is_running = False

        if is_running:
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

            summary = summary.replace("\n", " ").strip()
            while "  " in summary:
                summary = summary.replace("  ", " ")

            if len(summary) > 95:
                summary = summary[:92] + "..."

            short_id = conv_id[:8]
            active_tasks.append({
                "id": conv_id,
                "short_id": short_id,
                "title": f"Antigravity 2.0 • {task_state}",
                "summary": summary or "Active Antigravity task in progress...",
                "state": task_state,
                "age": round(age, 1)
            })

    return active_tasks

def get_current_task_status():
    """
    Checks if any Antigravity coding task/session is actively running.
    Returns: (is_running: bool, title: str, summary: str, tasks: list[dict])
    """
    try:
        tasks = get_all_active_tasks()
        if not tasks:
            return False, "", "", []

        t0 = tasks[0]
        return True, t0["title"], t0["summary"], tasks
    except Exception:
        return False, "", "", []

if __name__ == "__main__":
    is_active, title, summary, tasks = get_current_task_status()
    print("Active:", is_active)
    print("Tasks count:", len(tasks))
    print("Title:", title)
    print("Summary:", summary)

from langchain_core.tools import BaseTool

from app.agent.tools.email_tools import (
    draft_email_in_user_style,
    extract_action_items_from_email,
    list_attachments,
    list_unread_emails,
    save_attachments_by_topic,
    save_emails_by_topic,
    summarize_email,
)
from app.agent.tools.utility_tools import get_current_local_time, list_local_models_tool


def get_tools() -> list[BaseTool]:
    return [
        get_current_local_time,
        list_local_models_tool,
        list_unread_emails,
        summarize_email,
        extract_action_items_from_email,
        list_attachments,
        save_emails_by_topic,
        save_attachments_by_topic,
        draft_email_in_user_style,
    ]

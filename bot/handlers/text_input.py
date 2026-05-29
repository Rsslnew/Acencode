"""
Text Input Handler for Settings Menu.
Handles reply-based input for CRF, bitrate, caption, prefix, suffix, etc.
Also handles photo uploads for image watermark and custom thumbnail.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from bot.utils.user_settings import get_user_settings

logger = logging.getLogger(__name__)

# In-memory state: {user_id: {"action": "set_crf", "expires": datetime, "message_id": int}}
_user_input_states = {}

# Valid actions that require text input
TEXT_ACTIONS = {
    "set_crf": {
        "prompt": "Send the CRF value (0-51).\nLower = better quality, larger file.",
        "validate": lambda v: v.isdigit() and 0 <= int(v) <= 51,
        "error": "Invalid CRF! Must be a number between 0 and 51.",
        "setter": lambda s, v: setattr(s, "crf", int(v)),
        "success": "CRF updated to {}",
        "menu_callback": "sett:encode"
    },
    "set_vbitrate": {
        "prompt": "Send the video bitrate (e.g., 1000k, 2M).\nOr send 'disable' to use CRF mode.",
        "validate": lambda v: v.lower() == "disable" or (
            v[:-1].isdigit() and v[-1].lower() in ("k", "m")
        ),
        "error": "Invalid bitrate! Use format like 1000k, 2M, or 'disable'.",
        "setter": lambda s, v: setattr(s, "video_bitrate", None if v.lower() == "disable" else v),
        "success": "Video bitrate updated to {}",
        "menu_callback": "sett:encode"
    },
    "set_caption": {
        "prompt": "Send the caption text for uploaded videos.\nSend 'disable' to remove caption.",
        "validate": lambda v: True,
        "error": "Invalid caption.",
        "setter": lambda s, v: setattr(s, "caption", None if v.lower() == "disable" else v),
        "success": "Caption updated!",
        "menu_callback": "sett:tg_tools"
    },
    "set_prefix": {
        "prompt": "Send the prefix text to add before filenames.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid prefix.",
        "setter": lambda s, v: setattr(s, "prefix", None if v.lower() == "disable" else v),
        "success": "Prefix updated to: {}",
        "menu_callback": "sett:extra"
    },
    "set_suffix": {
        "prompt": "Send the suffix text to add after filenames.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid suffix.",
        "setter": lambda s, v: setattr(s, "suffix", None if v.lower() == "disable" else v),
        "success": "Suffix updated to: {}",
        "menu_callback": "sett:extra"
    },
    "set_split_size": {
        "prompt": "Send split size (e.g., 1.95GB, 2GB, 500MB).\nSend 'disable' for no splitting.",
        "validate": lambda v: v.lower() == "disable" or any(
            v.upper().endswith(u) for u in ("GB", "MB", "KB")
        ),
        "error": "Invalid size! Use format like 1.95GB, 500MB, or 'disable'.",
        "setter": lambda s, v: setattr(s, "split_size", None if v.lower() == "disable" else v.upper()),
        "success": "Split size updated to {}",
        "menu_callback": "sett:tg_tools"
    },
    "set_split_duration": {
        "prompt": "Send split duration in seconds (e.g., 300).\nSend 'disable' for no duration split.",
        "validate": lambda v: v.lower() == "disable" or v.isdigit(),
        "error": "Invalid duration! Must be a number in seconds.",
        "setter": lambda s, v: setattr(s, "split_duration", None if v.lower() == "disable" else int(v)),
        "success": "Split duration updated to {}s",
        "menu_callback": "sett:tg_tools"
    },
    "set_upload_chat": {
        "prompt": "Send the chat ID or username where uploads should be sent.\nSend 'disable' to reset to your DM.",
        "validate": lambda v: True,
        "error": "Invalid chat ID.",
        "setter": lambda s, v: setattr(s, "upload_chat", None if v.lower() == "disable" else v),
        "success": "Upload chat updated to: {}",
        "menu_callback": "sett:tg_tools"
    },
    "set_gdrive_id": {
        "prompt": "Send your Google Drive folder ID.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid Gdrive ID.",
        "setter": lambda s, v: setattr(s, "gdrive_id", None if v.lower() == "disable" else v),
        "success": "Gdrive ID updated!",
        "menu_callback": "sett:gdrive"
    },
    "set_index_url": {
        "prompt": "Send your Index URL.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid Index URL.",
        "setter": lambda s, v: setattr(s, "index_url", None if v.lower() == "disable" else v),
        "success": "Index URL updated!",
        "menu_callback": "sett:gdrive"
    },
    "set_text_watermark": {
        "prompt": "Send the watermark text.\nSend 'disable' to remove text watermark.",
        "validate": lambda v: True,
        "error": "Invalid watermark text.",
        "setter": lambda s, v: setattr(s, "text_watermark", None if v.lower() == "disable" else v),
        "success": "Text watermark updated!",
        "menu_callback": "sett:watermark"
    },
    "set_video_title": {
        "prompt": "Send the video title metadata.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid video title.",
        "setter": lambda s, v: _set_metadata(s, "video_title", v),
        "success": "Video title metadata updated!",
        "menu_callback": "sett_ex:metadata"
    },
    "set_video_author": {
        "prompt": "Send the video author metadata.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid video author.",
        "setter": lambda s, v: _set_metadata(s, "video_author", v),
        "success": "Video author metadata updated!",
        "menu_callback": "sett_ex:metadata"
    },
    "set_audio_title": {
        "prompt": "Send the audio title metadata.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid audio title.",
        "setter": lambda s, v: _set_metadata(s, "audio_title", v),
        "success": "Audio title metadata updated!",
        "menu_callback": "sett_ex:metadata"
    },
    "set_subtitle_title": {
        "prompt": "Send the subtitle title metadata.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid subtitle title.",
        "setter": lambda s, v: _set_metadata(s, "subtitle_title", v),
        "success": "Subtitle title metadata updated!",
        "menu_callback": "sett_ex:metadata"
    },
    "set_autorename_template": {
        "prompt": "Send the AutoRename template.\nUse {filename}, {resolution}, {codec}, {preset} as placeholders.\nSend 'disable' to remove.",
        "validate": lambda v: True,
        "error": "Invalid template.",
        "setter": lambda s, v: setattr(s, "autorename_template", None if v.lower() == "disable" else v),
        "success": "AutoRename template updated!",
        "menu_callback": "sett_ex:autorename"
    },
    "set_excluded_extensions": {
        "prompt": "Send excluded extensions separated by commas (e.g., .txt,.jpg,.png).\nSend 'disable' to clear.",
        "validate": lambda v: True,
        "error": "Invalid extensions.",
        "setter": lambda s, v: setattr(s, "excluded_extensions", None if v.lower() == "disable" else [x.strip() for x in v.split(",")]),
        "success": "Excluded extensions updated!",
        "menu_callback": "sett:extra"
    },
    "import_settings": {
        "prompt": "Send your settings JSON to import.",
        "validate": lambda v: True,
        "error": "Invalid JSON.",
        "setter": lambda s, v: _import_json(s, v),
        "success": "Settings imported successfully!",
        "menu_callback": "sett:back_main"
    },
}


def _set_metadata(settings, key, value):
    """Helper to set metadata field."""
    meta = settings.metadata
    meta[key] = None if value.lower() == "disable" else value
    settings.metadata = meta


def _import_json(settings, json_str):
    """Helper to import settings from JSON string."""
    import json
    data = json.loads(json_str)
    settings.import_dict(data)


def set_input_state(user_id: int, action: str, message_id: int = None):
    """Set user state to wait for text input."""
    _user_input_states[user_id] = {
        "action": action,
        "expires": datetime.now() + timedelta(minutes=5),
        "message_id": message_id
    }
    logger.info(f"Set input state for user {user_id}: {action}")


def clear_input_state(user_id: int):
    """Clear user input state."""
    if user_id in _user_input_states:
        del _user_input_states[user_id]


def get_input_state(user_id: int) -> dict:
    """Get current input state for user."""
    state = _user_input_states.get(user_id)
    if state and datetime.now() > state["expires"]:
        clear_input_state(user_id)
        return None
    return state


class TextInputHandler:
    """Handle text input replies and photo uploads for settings menu."""

    @staticmethod
    @Client.on_message(filters.text & filters.private)
    async def handle_text_input(client: Client, message: Message):
        """Handle text messages in private chat (for settings input)."""
        user_id = message.from_user.id
        state = get_input_state(user_id)

        if not state:
            await message.reply(
                "No active input session.\n"
                "Use /settings in a group to configure the bot."
            )
            return

        action = state["action"]

        # Handle photo-based actions (should not come here)
        if action in ("set_image_watermark", "set_custom_thumbnail"):
            await message.reply(
                "Please send a photo, not text.\n"
                "Or send /cancel to cancel."
            )
            return

        config = TEXT_ACTIONS.get(action)

        if not config:
            logger.error(f"Unknown action: {action}")
            clear_input_state(user_id)
            return

        value = message.text.strip()

        # Validate input
        if not config["validate"](value):
            await message.reply(
                f"{config['error']}\n\n"
                f"{config['prompt']}"
            )
            return

        # Apply setting
        settings = get_user_settings(user_id)
        try:
            config["setter"](settings, value)
            success_msg = config["success"].format(value)
            await message.reply(f"{success_msg}")
        except Exception as e:
            logger.error(f"Failed to set {action}: {e}")
            await message.reply(f"Failed to update setting.\nError: {str(e)}")
            return
        finally:
            clear_input_state(user_id)

        # Show back button to return to menu
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.reply(
            "Tap Back to return to settings menu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back", callback_data=config["menu_callback"])]
            ])
        )

    @staticmethod
    @Client.on_message(filters.photo & filters.private)
    async def handle_photo_input(client: Client, message: Message):
        """Handle photo uploads in private chat (for watermark and thumbnail)."""
        user_id = message.from_user.id
        state = get_input_state(user_id)

        if not state:
            await message.reply(
                "No active photo session.\n"
                "Go to settings first to upload a photo."
            )
            return

        action = state["action"]

        if action == "set_image_watermark":
            await _handle_image_watermark_photo(client, message, user_id)
        elif action == "set_custom_thumbnail":
            await _handle_custom_thumbnail_photo(client, message, user_id)
        else:
            await message.reply(
                "Unexpected photo upload.\n"
                "Please use the settings menu to upload photos."
            )
            clear_input_state(user_id)

    # --- Callback Handlers for Text Input ---

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_crf:set$"))
    async def cb_set_crf(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_crf", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_crf"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_vb:set$"))
    async def cb_set_vbitrate(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_vbitrate", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_vbitrate"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tg:set_cap$"))
    async def cb_set_caption(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_caption", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_caption"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tg:split_size$"))
    async def cb_set_split_size(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_split_size", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_split_size"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tg:split_dur$"))
    async def cb_set_split_duration(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_split_duration", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_split_duration"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tg:up_chat$"))
    async def cb_set_upload_chat(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_upload_chat", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_upload_chat"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_gd:gdrive_id$"))
    async def cb_set_gdrive_id(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_gdrive_id", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_gdrive_id"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_gd:index$"))
    async def cb_set_index_url(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_index_url", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_index_url"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_wm:text$"))
    async def cb_set_text_watermark(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_text_watermark", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_text_watermark"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_wm:image$"))
    async def cb_set_image_watermark(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_image_watermark", callback.message.id)
        await callback.message.edit_text(
            "**Image Watermark**\n\n"
            "Send a photo to the bot in private chat to set as watermark.\n"
            "Or send 'disable' in text to remove image watermark.",
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tg:thumb$"))
    async def cb_set_thumbnail(client: Client, callback: CallbackQuery):
        """Set input state for custom thumbnail upload."""
        user_id = callback.from_user.id
        set_input_state(user_id, "set_custom_thumbnail", callback.message.id)

        from bot.utils.thumbnail import has_custom_thumbnail
        has_thumb = has_custom_thumbnail(user_id)
        current = "Exists" if has_thumb else "Not set"

        text = (
            f"**Set Thumbnail**\n\n"
            f"Current: `{current}`\n\n"
            f"Send a photo to the bot in private chat to set as custom thumbnail.\n"
            f"Recommended size: 320x180 (16:9) or any square image."
        )

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Delete Thumbnail", callback_data="sett_tg:del_thumb")],
            [InlineKeyboardButton("Back", callback_data="sett:tg_tools")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_input")],
        ])

        await callback.message.edit_text(text, reply_markup=buttons)

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tg:del_thumb$"))
    async def cb_delete_thumbnail(client: Client, callback: CallbackQuery):
        """Delete user's custom thumbnail."""
        user_id = callback.from_user.id
        from bot.utils.thumbnail import delete_custom_thumbnail

        if delete_custom_thumbnail(user_id):
            await callback.answer("Custom thumbnail deleted!")
        else:
            await callback.answer("No custom thumbnail to delete.")

        from bot.handlers.settings import SettingsHandler
        await SettingsHandler.cb_tg_tools(client, callback)

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tg:thumb_layout$"))
    async def cb_thumbnail_layout(client: Client, callback: CallbackQuery):
        """Show thumbnail layout options."""
        user_id = callback.from_user.id
        settings = get_user_settings(user_id)
        current = settings.thumbnail_layout or "default"

        text = (
            f"**Thumbnail Layout**\n\n"
            f"Current: `{current}`"
        )

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Default", callback_data="sett_tl:default")],
            [InlineKeyboardButton("Square Crop", callback_data="sett_tl:square")],
            [InlineKeyboardButton("Wide Crop", callback_data="sett_tl:wide")],
            [InlineKeyboardButton("Back", callback_data="sett:tg_tools")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_input")],
        ])

        await callback.message.edit_text(text, reply_markup=buttons)

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_tl:(.+)$"))
    async def cb_set_thumbnail_layout(client: Client, callback: CallbackQuery):
        """Set thumbnail layout."""
        layout = callback.data.split(":")[1]
        user_id = callback.from_user.id
        settings = get_user_settings(user_id)
        settings.thumbnail_layout = layout

        await callback.answer(f"Thumbnail layout set to {layout}!")

        from bot.handlers.settings import SettingsHandler
        await SettingsHandler.cb_tg_tools(client, callback)

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_meta:vtitle$"))
    async def cb_set_video_title(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_video_title", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_video_title"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_meta:vauthor$"))
    async def cb_set_video_author(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_video_author", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_video_author"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_meta:atitle$"))
    async def cb_set_audio_title(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_audio_title", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_audio_title"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_meta:stitle$"))
    async def cb_set_subtitle_title(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_subtitle_title", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_subtitle_title"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_ex:prefix$"))
    async def cb_set_prefix(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_prefix", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_prefix"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_ex:suffix$"))
    async def cb_set_suffix(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_suffix", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_suffix"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_ar:template$"))
    async def cb_set_ar_template(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_autorename_template", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_autorename_template"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett_ee:set$"))
    async def cb_set_excluded_ext(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "set_excluded_extensions", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["set_excluded_extensions"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^sett:import$"))
    async def cb_import_settings(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        set_input_state(user_id, "import_settings", callback.message.id)
        await callback.message.edit_text(
            TEXT_ACTIONS["import_settings"]["prompt"],
            reply_markup=_build_cancel_input_kb()
        )

    @staticmethod
    @Client.on_callback_query(filters.regex(r"^cancel_input$"))
    async def cb_cancel_input(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        clear_input_state(user_id)
        await callback.answer("Input cancelled.")
        from bot.handlers.settings import SettingsHandler
        await SettingsHandler.cb_back_main(client, callback)


# === Photo Handlers ===

async def _handle_image_watermark_photo(client, message, user_id):
    """Handle photo upload for image watermark."""
    from bot.config import Config
    from bot.utils.thumbnail import get_user_thumb_dir

    wm_dir = get_user_thumb_dir(user_id)
    wm_path = wm_dir / "watermark.png"

    try:
        await message.download(file_name=str(wm_path))

        settings = get_user_settings(user_id)
        settings.image_watermark = str(wm_path)

        await message.reply(
            f"Image watermark saved!\n"
            f"Path: `{wm_path}`"
        )
    except Exception as e:
        logger.error(f"Failed to save watermark: {e}")
        await message.reply(f"Error saving watermark image.\nError: {str(e)}")
    finally:
        clear_input_state(user_id)

    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await message.reply(
        "Tap Back to return to settings menu.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="sett:watermark")]
        ])
    )


async def _handle_custom_thumbnail_photo(client, message, user_id):
    """Handle photo upload for custom thumbnail."""
    from bot.utils.thumbnail import get_custom_thumbnail_path

    thumb_path = get_custom_thumbnail_path(user_id)

    try:
        await message.download(file_name=str(thumb_path))

        if thumb_path.exists() and thumb_path.stat().st_size > 0:
            await message.reply(
                f"Custom thumbnail saved!\n"
                f"It will be used for all your future uploads."
            )
        else:
            await message.reply("Failed to save thumbnail. Please try again.")

    except Exception as e:
        logger.error(f"Failed to save custom thumbnail: {e}")
        await message.reply(f"Error saving thumbnail.\nError: {str(e)}")

    finally:
        clear_input_state(user_id)

    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await message.reply(
        "Tap Back to return to settings menu.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="sett:tg_tools")]
        ])
    )


def _build_cancel_input_kb():
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Cancel", callback_data="cancel_input")]
    ])

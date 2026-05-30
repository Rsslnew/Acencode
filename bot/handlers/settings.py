"""
Settings Handler v3 - Module-level functions, no decorators.
"""
import json
import logging
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from bot.utils.user_settings import get_user_settings, UserSettings

logger = logging.getLogger(__name__)


# ============ KEYBOARD BUILDERS (sama, tidak berubah) ============

def _build_main_menu(settings: UserSettings) -> InlineKeyboardMarkup:
    dest = settings.upload_destination.capitalize()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Default Upload | {dest}", callback_data="sett:upload_dest")],
        [
            InlineKeyboardButton("Encode Tools", callback_data="sett:encode"),
            InlineKeyboardButton("Watermark Tools", callback_data="sett:watermark"),
        ],
        [
            InlineKeyboardButton("TG Tools", callback_data="sett:tg_tools"),
            InlineKeyboardButton("Rclone Tools", callback_data="sett:rclone"),
        ],
        [
            InlineKeyboardButton("Gdrive Tools", callback_data="sett:gdrive"),
            InlineKeyboardButton("GoFile Tools", callback_data="sett:gofile"),
        ],
        [
            InlineKeyboardButton("Extra Tools", callback_data="sett:extra"),
            InlineKeyboardButton("Reset All", callback_data="sett:reset"),
        ],
        [
            InlineKeyboardButton("Export Settings", callback_data="sett:export"),
            InlineKeyboardButton("Import Settings", callback_data="sett:import"),
        ],
        [InlineKeyboardButton("Close", callback_data="sett:close")],
    ])


def _build_upload_dest_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Gdrive", callback_data="sett_dest:gdrive")],
        [InlineKeyboardButton("Rclone", callback_data="sett_dest:rclone")],
        [InlineKeyboardButton("GoFile", callback_data="sett_dest:gofile")],
        [InlineKeyboardButton("Telegram", callback_data="sett_dest:telegram")],
        [
            InlineKeyboardButton("Back", callback_data="sett:back_main"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])


def _build_encode_menu(settings: UserSettings):
    vc = settings.video_codec
    preset = settings.preset
    crf = settings.crf
    vbr = settings.video_bitrate or "Not Set"
    res = settings.resolution
    ac = settings.audio_codec
    abr = settings.audio_bitrate

    text = (
        f"**Encode Settings**\n\n"
        f"Video Codec is `{vc}`\n"
        f"Preset is `{preset}`\n"
        f"CRF is `{crf}`\n"
        f"Video Bitrate is `{vbr}`\n"
        f"Resolution is `{res}`\n"
        f"Audio Codec is `{ac}`\n"
        f"Audio Bitrate is `{abr}`"
    )
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Video Codec", callback_data="sett_enc:video_codec"),
            InlineKeyboardButton("Preset", callback_data="sett_enc:preset"),
        ],
        [
            InlineKeyboardButton("CRF", callback_data="sett_enc:crf"),
            InlineKeyboardButton("Video Bitrate", callback_data="sett_enc:vbitrate"),
        ],
        [InlineKeyboardButton("Resolution", callback_data="sett_enc:resolution")],
        [
            InlineKeyboardButton("Audio Codec", callback_data="sett_enc:audio_codec"),
            InlineKeyboardButton("Audio Bitrate", callback_data="sett_enc:abitrate"),
        ],
        [
            InlineKeyboardButton("Back", callback_data="sett:back_main"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])
    return text, buttons


def _build_video_codec_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("libx264", callback_data="sett_vc:libx264")],
        [InlineKeyboardButton("libx265", callback_data="sett_vc:libx265")],
        [InlineKeyboardButton("Back", callback_data="sett:encode")],
    ])


def _build_preset_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ultrafast", callback_data="sett_pr:ultrafast"),
            InlineKeyboardButton("superfast", callback_data="sett_pr:superfast"),
            InlineKeyboardButton("veryfast", callback_data="sett_pr:veryfast"),
        ],
        [
            InlineKeyboardButton("faster", callback_data="sett_pr:faster"),
            InlineKeyboardButton("fast", callback_data="sett_pr:fast"),
            InlineKeyboardButton("medium", callback_data="sett_pr:medium"),
        ],
        [InlineKeyboardButton("Back", callback_data="sett:encode")],
    ])


def _build_resolution_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1080p", callback_data="sett_res:1080"),
            InlineKeyboardButton("720p", callback_data="sett_res:720"),
        ],
        [
            InlineKeyboardButton("480p", callback_data="sett_res:480"),
            InlineKeyboardButton("360p", callback_data="sett_res:360"),
        ],
        [InlineKeyboardButton("240p", callback_data="sett_res:240")],
        [InlineKeyboardButton("Back", callback_data="sett:encode")],
    ])


def _build_audio_codec_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("copy", callback_data="sett_ac:copy"),
            InlineKeyboardButton("aac", callback_data="sett_ac:aac"),
            InlineKeyboardButton("mp3", callback_data="sett_ac:mp3"),
        ],
        [
            InlineKeyboardButton("flac", callback_data="sett_ac:flac"),
            InlineKeyboardButton("opus", callback_data="sett_ac:opus"),
            InlineKeyboardButton("ac3", callback_data="sett_ac:ac3"),
        ],
        [InlineKeyboardButton("wav", callback_data="sett_ac:wav")],
        [InlineKeyboardButton("Back", callback_data="sett:encode")],
    ])


def _build_audio_bitrate_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("copy", callback_data="sett_ab:copy"),
            InlineKeyboardButton("128k", callback_data="sett_ab:128k"),
            InlineKeyboardButton("192k", callback_data="sett_ab:192k"),
        ],
        [
            InlineKeyboardButton("256k", callback_data="sett_ab:256k"),
            InlineKeyboardButton("320k", callback_data="sett_ab:320k"),
        ],
        [InlineKeyboardButton("Back", callback_data="sett:encode")],
    ])


def _build_watermark_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Text Watermark", callback_data="sett_wm:text")],
        [InlineKeyboardButton("Image Watermark", callback_data="sett_wm:image")],
        [InlineKeyboardButton("Set Position", callback_data="sett_wm:position")],
        [
            InlineKeyboardButton("Back", callback_data="sett:back_main"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])


def _build_wm_position_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Top Left", callback_data="sett_wpos:top-left"),
            InlineKeyboardButton("Top Right", callback_data="sett_wpos:top-right"),
        ],
        [
            InlineKeyboardButton("Bottom Left", callback_data="sett_wpos:bottom-left"),
            InlineKeyboardButton("Bottom Right", callback_data="sett_wpos:bottom-right"),
        ],
        [InlineKeyboardButton("Center", callback_data="sett_wpos:center")],
        [
            InlineKeyboardButton("Back", callback_data="sett:watermark"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])


def _build_tg_tools_menu(settings: UserSettings):
    ut = settings.upload_type
    ss = settings.split_size
    sd = settings.split_duration or "None"
    es = "Enabled" if settings.equal_splits else "Disabled"
    se = "True" if settings.spoiler_effect else "False"
    cam = "True" if settings.caption_above_media else "False"
    uc = settings.upload_chat or "None"
    tl = settings.thumbnail_layout or "None"
    dt = "True" if settings.disable_thumbnail else "False"
    cap = settings.caption or "None"

    text = (
        f"**TG Upload Settings**\n\n"
        f"Upload Type is `{ut}`\n"
        f"Split Size is `{ss}`\n"
        f"Split Duration is `{sd}`\n"
        f"Equal Splits is `{es}`\n"
        f"Spoiler Effect is `{se}`\n"
        f"Caption Above Media is `{cam}`\n"
        f"Upload Chat is `{uc}`\n"
        f"Thumbnail Layout is `{tl}`\n"
        f"Disable Thumbnail is `{dt}`\n"
        f"Caption is `{cap}`"
    )
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Set Thumbnail", callback_data="sett_tg:thumb"),
            InlineKeyboardButton("Disable Thumbnail", callback_data="sett_tg:dis_thumb"),
        ],
        [
            InlineKeyboardButton("Send As Document", callback_data="sett_tg:doc"),
            InlineKeyboardButton("Split Size", callback_data="sett_tg:split_size"),
        ],
        [
            InlineKeyboardButton("Split Duration", callback_data="sett_tg:split_dur"),
            InlineKeyboardButton("Equal Splits", callback_data="sett_tg:eq_split"),
        ],
        [
            InlineKeyboardButton("Spoiler Effect", callback_data="sett_tg:spoiler"),
            InlineKeyboardButton("Caption Above Media", callback_data="sett_tg:cap_above"),
        ],
        [
            InlineKeyboardButton("Add Upload Chat", callback_data="sett_tg:up_chat"),
            InlineKeyboardButton("Set Caption", callback_data="sett_tg:set_cap"),
        ],
        [InlineKeyboardButton("Set Thumbnail Layout", callback_data="sett_tg:thumb_layout")],
        [InlineKeyboardButton("Screenshot Count", callback_data="sett_tg:ss_count")],
        [
            InlineKeyboardButton("Back", callback_data="sett:back_main"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])
    return text, buttons


def _build_gdrive_menu(settings: UserSettings):
    gt = "Exists" if settings.gdrive_token else "Not Exists"
    gid = settings.gdrive_id or "None"
    iu = settings.index_url or "None"
    sd = "Enabled" if settings.stop_duplicate else "Disabled"

    text = (
        f"**Gdrive API Settings**\n\n"
        f"Gdrive Token `{gt}`\n"
        f"Gdrive ID is `{gid}`\n"
        f"Index URL is `{iu}`\n"
        f"Stop Duplicate is `{sd}`"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("token.pickle", callback_data="sett_gd:token")],
        [InlineKeyboardButton("Default Gdrive ID", callback_data="sett_gd:gdrive_id")],
        [InlineKeyboardButton("Index URL", callback_data="sett_gd:index")],
        [InlineKeyboardButton("Enable Stop Duplicate", callback_data="sett_gd:stop_dup")],
        [
            InlineKeyboardButton("Back", callback_data="sett:back_main"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])
    return text, buttons


def _build_extra_menu(settings: UserSettings):
    rr = settings.get("remove_replace_words", {})
    regex_m = rr.get("regex") or "None"
    simple_m = rr.get("simple") or "None"
    prefix = settings.prefix or "None"
    suffix = settings.suffix or "None"
    meta = settings.metadata
    meta_en = "Enabled" if any(meta.values()) else "Disabled"
    att = settings.get("attachment_photo") or settings.get("attachment_url") or "None"
    art = settings.autorename_template or "None"
    arm = settings.autorename_mode.capitalize()
    ee = settings.excluded_extensions or "None"

    text = (
        f"**Extra Settings**\n\n"
        f"Remove/Replace Words:\n"
        f"- Regex Method is `{regex_m}`\n"
        f"- Simple Method is `{simple_m}`\n"
        f"Prefix is `{prefix}`\n"
        f"Suffix is `{suffix}`\n"
        f"Metadata is `{meta_en}`\n"
        f"Attachment is `{att}`\n"
        f"AutoRename Template is `{art}`\n"
        f"Excluded Extensions is `{ee}`"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Remove/Replace Words", callback_data="sett_ex:rr_words")],
        [
            InlineKeyboardButton("Set Prefix", callback_data="sett_ex:prefix"),
            InlineKeyboardButton("Set Suffix", callback_data="sett_ex:suffix"),
        ],
        [
            InlineKeyboardButton("Metadata", callback_data="sett_ex:metadata"),
            InlineKeyboardButton("AutoRename", callback_data="sett_ex:autorename"),
        ],
        [
            InlineKeyboardButton("Attachment Photo", callback_data="sett_ex:att_photo"),
            InlineKeyboardButton("Attachment URL", callback_data="sett_ex:att_url"),
        ],
        [InlineKeyboardButton("Excluded Extensions", callback_data="sett_ex:excl_ext")],
        [
            InlineKeyboardButton("Back", callback_data="sett:back_main"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])
    return text, buttons


def _build_metadata_menu(settings: UserSettings):
    meta = settings.metadata
    vt = meta.get("video_title") or "None"
    va = meta.get("video_author") or "None"
    at = meta.get("audio_title") or "None"
    st = meta.get("subtitle_title") or "None"

    text = (
        f"**Metadata Setting**\n\n"
        f"Video Title is `{vt}`\n"
        f"Video Author is `{va}`\n"
        f"Audio Title is `{at}`\n"
        f"Subtitle Title is `{st}`"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Set Video Title", callback_data="sett_meta:vtitle")],
        [InlineKeyboardButton("Set Video Author", callback_data="sett_meta:vauthor")],
        [InlineKeyboardButton("Set Audio Title", callback_data="sett_meta:atitle")],
        [InlineKeyboardButton("Set Subtitle Title", callback_data="sett_meta:stitle")],
        [
            InlineKeyboardButton("Back", callback_data="sett_ex:metadata"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])
    return text, buttons


def _build_autorename_menu(settings: UserSettings):
    art = settings.autorename_template or "None"
    arm = settings.autorename_mode.capitalize()

    text = (
        f"**AutoRename Settings**\n\n"
        f"Template is `{art}`\n"
        f"Mode is `{arm}`"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Set Template", callback_data="sett_ar:template")],
        [InlineKeyboardButton(f"Mode | {arm}", callback_data="sett_ar:mode")],
        [
            InlineKeyboardButton("Back", callback_data="sett_ex:autorename"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])
    return text, buttons


def _build_autorename_mode_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Regex", callback_data="sett_arm:regex"),
            InlineKeyboardButton("Other", callback_data="sett_arm:other"),
        ],
        [InlineKeyboardButton("AI Mode", callback_data="sett_arm:ai")],
        [
            InlineKeyboardButton("Back", callback_data="sett_ex:autorename"),
            InlineKeyboardButton("Close", callback_data="sett:close"),
        ],
    ])


# ============ COMMAND HANDLER ============

async def settings_command(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    settings = get_user_settings(user_id)

    text = (
        f"**Settings for** [{username}](tg://user?id={user_id})\n\n"
        f"Default Upload is `{settings.upload_destination.capitalize()}`\n"
        f"Using MY token/config"
    )
    await message.reply_text(
        text,
        reply_markup=_build_main_menu(settings)
    )


# ============ CALLBACK HANDLERS ============

async def cb_upload_dest(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Upload Destination Settings**\n\nChoose destination:",
        reply_markup=_build_upload_dest_menu()
    )


async def cb_encode(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    text, buttons = _build_encode_menu(settings)
    await callback.message.edit_text(text, reply_markup=buttons)


async def cb_watermark(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    tw = settings.text_watermark or "None"
    iw = settings.image_watermark or "None"
    pos = settings.watermark_position

    text = (
        f"**Watermark Settings**\n\n"
        f"You can set both a text watermark and an image watermark at the same time. "
        f"If both are configured, the video will have both added.\n\n"
        f"Text Watermark: `{tw}`\n"
        f"Image Watermark: `{iw}`\n"
        f"Position: `{pos}`"
    )
    await callback.message.edit_text(text, reply_markup=_build_watermark_menu())


async def cb_tg_tools(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    text, buttons = _build_tg_tools_menu(settings)
    await callback.message.edit_text(text, reply_markup=buttons)


async def cb_gdrive(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    text, buttons = _build_gdrive_menu(settings)
    await callback.message.edit_text(text, reply_markup=buttons)


async def cb_gofile(client, callback: CallbackQuery):
    await callback.answer("GoFile settings coming soon!", show_alert=True)


async def cb_rclone(client, callback: CallbackQuery):
    await callback.answer("Rclone settings coming soon!", show_alert=True)


async def cb_extra(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    text, buttons = _build_extra_menu(settings)
    await callback.message.edit_text(text, reply_markup=buttons)


async def cb_reset(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.reset()
    await callback.answer("All settings reset to default!", show_alert=True)
    await cb_back_main(client, callback)


async def cb_export(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    data = settings.export_dict()
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    await callback.message.reply_text(
        f"**Export Settings**\n\n`{json_str}`\n\n"
        f"Copy this JSON to import later.",
        quote=True
    )
    await callback.answer("Settings exported!")


async def cb_import(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Import Settings**\n\n"
        "Reply to this message with your settings JSON to import.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="sett:back_main")],
        ])
    )


async def cb_close(client, callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass


async def cb_back_main(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    settings = get_user_settings(user_id)
    text = (
        f"**Settings for** [{username}](tg://user?id={user_id})\n\n"
        f"Default Upload is `{settings.upload_destination.capitalize()}`\n"
        f"Using MY token/config"
    )
    await callback.message.edit_text(
        text,
        reply_markup=_build_main_menu(settings)
    )


# --- Upload Destination ---

async def cb_set_dest(client, callback: CallbackQuery):
    dest = callback.data.split(":")[1]
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.upload_destination = dest
    await callback.answer(f"Upload destination set to {dest.capitalize()}!")
    await cb_back_main(client, callback)


# --- Encode Sub-menus ---

async def cb_enc_vc(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Encode Codec**\n\nSelect a codec for video encoding.",
        reply_markup=_build_video_codec_menu()
    )


async def cb_enc_preset(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Encode Preset**\n\nSelect a preset for video encoding.",
        reply_markup=_build_preset_menu()
    )


async def cb_enc_crf(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Edit CRF**\n\nCurrent Value: (send value in chat)\n\n"
        "Range: 0-51 (lower = better quality, larger file)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Set", callback_data="sett_crf:set")],
            [InlineKeyboardButton("Back", callback_data="sett:encode")],
            [InlineKeyboardButton("Close", callback_data="sett:close")],
        ])
    )


async def cb_enc_vbitrate(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Edit Video Bitrate**\n\nCurrent Value: (send value in chat)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Set", callback_data="sett_vb:set")],
            [InlineKeyboardButton("Back", callback_data="sett:encode")],
            [InlineKeyboardButton("Close", callback_data="sett:close")],
        ])
    )


async def cb_enc_resolution(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Encode Resolution**\n\nSelect a resolution.",
        reply_markup=_build_resolution_menu()
    )


async def cb_enc_ac(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Audio Codec**\n\nSelect an audio codec.",
        reply_markup=_build_audio_codec_menu()
    )


async def cb_enc_ab(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Audio Bitrate**\n\nSelect an audio bitrate.",
        reply_markup=_build_audio_bitrate_menu()
    )


# --- Encode Value Setters ---

async def cb_set_vc(client, callback: CallbackQuery):
    codec = callback.data.split(":")[1]
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.video_codec = codec
    await callback.answer(f"Video codec set to {codec}!")
    await cb_encode(client, callback)


async def cb_set_preset(client, callback: CallbackQuery):
    preset = callback.data.split(":")[1]
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.preset = preset
    await callback.answer(f"Preset set to {preset}!")
    await cb_encode(client, callback)


async def cb_set_res(client, callback: CallbackQuery):
    res = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.resolution = res
    await callback.answer(f"Resolution set to {res}p!")
    await cb_encode(client, callback)


async def cb_set_ac(client, callback: CallbackQuery):
    codec = callback.data.split(":")[1]
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.audio_codec = codec
    await callback.answer(f"Audio codec set to {codec}!")
    await cb_encode(client, callback)


async def cb_set_ab(client, callback: CallbackQuery):
    bitrate = callback.data.split(":")[1]
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.audio_bitrate = bitrate
    await callback.answer(f"Audio bitrate set to {bitrate}!")
    await cb_encode(client, callback)


# --- Watermark ---

async def cb_wm_position(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    current = settings.watermark_position
    await callback.message.edit_text(
        f"**Watermark Position**\n\nCurrent: `{current}`",
        reply_markup=_build_wm_position_menu()
    )


async def cb_set_wm_position(client, callback: CallbackQuery):
    pos = callback.data.split(":")[1]
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.watermark_position = pos
    await callback.answer(f"Watermark position set to {pos}!")
    await cb_watermark(client, callback)


# --- Extra Sub-menus ---

async def cb_ex_metadata(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    text, buttons = _build_metadata_menu(settings)
    await callback.message.edit_text(text, reply_markup=buttons)


async def cb_ex_autorename(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    text, buttons = _build_autorename_menu(settings)
    await callback.message.edit_text(text, reply_markup=buttons)


async def cb_ar_mode(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Choose AutoRename mode!**",
        reply_markup=_build_autorename_mode_menu()
    )


async def cb_set_arm(client, callback: CallbackQuery):
    mode = callback.data.split(":")[1]
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.autorename_mode = mode
    await callback.answer(f"AutoRename mode set to {mode.capitalize()}!")
    await cb_ex_autorename(client, callback)


async def cb_ex_excl_ext(client, callback: CallbackQuery):
    await callback.message.edit_text(
        "**Edit Excluded Extensions**\n\nCurrent Value:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Set", callback_data="sett_ee:set")],
            [InlineKeyboardButton("Back", callback_data="sett:extra")],
            [InlineKeyboardButton("Close", callback_data="sett:close")],
        ])
    )


# --- Screenshot ---

async def cb_screenshot_count(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    current = settings.get("screenshot_count", 3)

    text = (
        f"**Screenshot Count**\n\n"
        f"Current: `{current}` screenshots\n\n"
        f"Choose how many screenshots to generate per video."
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data="sett_ss:1"),
         InlineKeyboardButton("3", callback_data="sett_ss:3"),
         InlineKeyboardButton("5", callback_data="sett_ss:5")],
        [InlineKeyboardButton("Disable", callback_data="sett_ss:0")],
        [InlineKeyboardButton("Back", callback_data="sett:tg_tools")],
        [InlineKeyboardButton("Close", callback_data="sett:close")],
    ])

    await callback.message.edit_text(text, reply_markup=buttons)


async def cb_set_screenshot_count(client, callback: CallbackQuery):
    count = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.set("screenshot_count", count)

    if count == 0:
        await callback.answer("Screenshots disabled!")
    else:
        await callback.answer(f"Screenshot count set to {count}!")

    await cb_tg_tools(client, callback)


# --- TG Tools Toggles ---

async def cb_tg_doc(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    new_type = "DOCUMENT" if settings.upload_type == "MEDIA" else "MEDIA"
    settings.upload_type = new_type
    await callback.answer(f"Upload type set to {new_type}!")
    await cb_tg_tools(client, callback)


async def cb_tg_spoiler(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.spoiler_effect = not settings.spoiler_effect
    await callback.answer(f"Spoiler effect: {settings.spoiler_effect}!")
    await cb_tg_tools(client, callback)


async def cb_tg_eqsplit(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.equal_splits = not settings.equal_splits
    await callback.answer(f"Equal splits: {settings.equal_splits}!")
    await cb_tg_tools(client, callback)


async def cb_tg_capabove(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.caption_above_media = not settings.caption_above_media
    await callback.answer(f"Caption above media: {settings.caption_above_media}!")
    await cb_tg_tools(client, callback)


async def cb_tg_disthumb(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.disable_thumbnail = not settings.disable_thumbnail
    await callback.answer(f"Disable thumbnail: {settings.disable_thumbnail}!")
    await cb_tg_tools(client, callback)


# --- Gdrive Toggles ---

async def cb_gd_stopdup(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings.stop_duplicate = not settings.stop_duplicate
    await callback.answer(f"Stop duplicate: {settings.stop_duplicate}!")
    await cb_gdrive(client, callback)

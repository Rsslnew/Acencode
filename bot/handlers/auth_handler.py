"""
Auth Handler v3 - Module-level functions for Pyrogram.
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.auth import verify_user, is_verified
from bot.utils.safelinku import generate_token, verify_token, get_verify_safelink_text, get_verification_link

logger = logging.getLogger(__name__)


@Client.on_callback_query(filters.regex(r"^verify_me$"))
async def verify_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name

    if is_verified(user_id):
        await callback.answer("Kamu sudah verified!", show_alert=False)
        try:
            await callback.message.edit_text(
                f"✅ **@{username} sudah verified!**\n"
                f"Langsung kirim video ke grup untuk compress."
            )
        except Exception:
            pass
        return

    # Generate token acak
    token = generate_token()
    store_token(user_id, token)  # store di safelinku.py
    safelink_url = await get_verification_link(user_id, username)

    await callback.answer("Link verifikasi dibuat!", show_alert=False)

    try:
        await callback.message.edit_text(
            get_verify_safelink_text(user_id, username),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Verify (Lewati Iklan)", url=safelink_url)],
                [InlineKeyboardButton("🔄 Refresh Token", callback_data="refresh_token")]
            ]),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to edit verify message: {e}")


@Client.on_callback_query(filters.regex(r"^refresh_token$"))
async def refresh_token_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name

    if is_verified(user_id):
        await callback.answer("Sudah verified!", show_alert=False)
        return

    token = generate_token()
    store_token(user_id, token)
    safelink_url = await get_verification_link(user_id, username)

    await callback.answer("Token baru dibuat!", show_alert=False)

    try:
        await callback.message.edit_text(
            get_verify_safelink_text(user_id, username),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Verify (Lewati Iklan)", url=safelink_url)],
                [InlineKeyboardButton("🔄 Refresh Token", callback_data="refresh_token")]
            ]),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")


@Client.on_message(filters.private & filters.command("start"))
async def start_command(client: Client, message):
    """Handle /start <token> dari SafeLinkU redirect."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Cek apakah sudah verified
    if is_verified(user_id):
        await message.reply(
            f"✅ **@{username} sudah verified!**\n\n"
            f"Silakan kirim video ke grup untuk compress.\n"
            f"Bot tidak menerima video via DM."
        )
        return

    # Parse token dari command
    args = message.text.split()
    if len(args) < 2:
        await message.reply(
            f"👋 **Halo @{username}!**\n\n"
            f"Untuk menggunakan bot, silakan:\n"
            f"1. Join grup yang menggunakan bot ini\n"
            f"2. Kirim video ke grup\n"
            f"3. Klik tombol **Verify** dan lewati iklan\n"
            f"4. Kamu akan diarahkan ke sini untuk verifikasi otomatis"
        )
        return

    token = args[1]

    # Validasi token
    if verify_token(user_id, token):
        verify_user(user_id, username)
        await message.reply(
            f"🎉 **Verifikasi Berhasil!**\n\n"
            f"✅ @{username} telah verified!\n"
            f"Sekarang kamu bisa kirim video ke grup untuk compress.\n\n"
            f"📌 **Tips:**\n"
            f"• Kirim video ke grup (bukan DM)\n"
            f"• Video akan otomatis dihapus dan diproses\n"
            f"• Hasil dikirim ke DM kamu"
        )
    else:
        await message.reply(
            f"❌ **Token Tidak Valid!**\n\n"
            f"Kemungkinan:\n"
            f"• Token sudah digunakan\n"
            f"• Token expired\n"
            f"• Token bukan milikmu\n\n"
            f"Silakan kembali ke grup dan klik **Verify** ulang."
        )

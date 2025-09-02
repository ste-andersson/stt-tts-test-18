# app/llm/send_response_to_tts.py
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("llm")

async def send_llm_response_to_tts(ws, llm_response: str) -> bool:
    """
    Skicka LLM-svar till TTS för konvertering till audio.
    
    Args:
        ws: WebSocket-anslutning till frontend
        llm_response: Text från LLM som ska konverteras till audio
        
    Returns:
        True om TTS-anropet lyckades, False annars
    """
    if not llm_response or not llm_response.strip():
        logger.warning("Empty LLM response, skipping TTS")
        return False
    
    try:
        # Importera TTS-funktionalitet
        from ..tts.text_to_audio import process_text_to_audio
        from ..tts.send_audio_to_frontend import send_audio_to_frontend
        
        logger.info("Starting TTS conversion for LLM response: %s", llm_response[:50])
        
        # Skicka status till frontend
        await ws.send_json({
            "type": "status",
            "stage": "llm_response_ready",
            "text": llm_response
        })
        
        # Processa text till audio
        audio_bytes_total = 0
        last_chunk_ts = None
        
        async for server_msg, current_audio_bytes in process_text_to_audio(ws, llm_response, asyncio.get_event_loop().time()):
            # Skicka audio till frontend
            audio_bytes_total, last_chunk_ts, should_break = await send_audio_to_frontend(
                ws, server_msg, current_audio_bytes, last_chunk_ts
            )
            
            if should_break:
                break
        
        logger.info("Successfully sent LLM response as audio: %d bytes", audio_bytes_total)
        
        # Skicka completion-status
        await ws.send_json({
            "type": "status",
            "stage": "conversation_complete",
            "audio_bytes_total": audio_bytes_total
        })
        
        return True
        
    except Exception as e:
        logger.error("Error sending LLM response to TTS: %s", str(e))
        
        # Skicka felmeddelande till frontend
        try:
            await ws.send_json({
                "type": "error",
                "message": f"TTS conversion failed: {str(e)}"
            })
        except Exception:
            pass
        
        return False

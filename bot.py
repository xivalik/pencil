async def stream_grammar_correction(text, language, message):
    try:
        stream = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPTS[language]},
                {"role": "user", "content": f"Check this English text:\n{text}"}
            ],
            max_tokens=1500,
            temperature=0.2,
            stream=True
        )

        full_text = ""
        buffer = ""

        last_edit = asyncio.get_event_loop().time()

        async def safe_edit(new_text):
            """Ensures edits happen max once per second."""
            nonlocal last_edit
            now = asyncio.get_event_loop().time()

            # Do NOT edit too fast
            if now - last_edit < 1.0:
                return

            last_edit = now
            try:
                await message.edit_text(new_text, parse_mode="HTML")
            except:
                pass

        # Stream processing
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if not delta:
                continue

            buffer += delta

            now = asyncio.get_event_loop().time()
            if now - last_edit >= 1.0:  # One update per 1 sec
                full_text += buffer
                buffer = ""

                preview = full_text + "▌"
                await safe_edit(preview)

        # Final content
        full_text += buffer

        if "NO_ERRORS_FOUND" in full_text:
            await message.edit_text(LANGUAGES[language]["no_error"], parse_mode="HTML")
        else:
            await message.edit_text(full_text, parse_mode="HTML")

    except Exception as e:
        await message.edit_text("❌ Error: " + str(e))

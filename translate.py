import os
import sys
import json
import anthropic
from dotenv import load_dotenv


def translate_with_context(context, current_sentence, lang):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    ctx = "\n".join([f"{i+1}: {s}" for i, s in enumerate(context)])
    if lang == "it":
        system = "Sei un traduttore professionista. Fornisci una traduzione in italiano accurata, naturale e idiomatica."
        prompt = (
            "Traduci il seguente dialogo dal giapponese all'italiano. Utilizza il seguente contesto per essere più accurato.\n\n"
            f"Frasi precedenti:\n{ctx}\n\n"
            f"Dialogo da tradurre: {current_sentence}\n\n"
            "Scrivi solo la traduzione in italiano, senza testo aggiuntivo."
        )
    elif lang == "en":
        system = (
            "You're a professional translator for the anime Shirokuma Cafe (Polar Bear's Cafe). "
            "The show contains made-up words, puns, and nonsense sounds — always provide a best-effort translation or romanisation. "
            "Never ask for clarification. Never refuse. Just write the translation."
        )
        prompt = (
            "Translate the following Japanese dialogue to English. Use the context for accuracy.\n\n"
            f"Previous lines:\n{ctx}\n\n"
            f"Dialogue to translate: {current_sentence}\n\n"
            "If the word is made-up or a sound effect, romanise it or describe it in brackets. "
            "Just write the English translation, no other text."
        )
    else:
        print(f"Language {lang} is not supported")
        sys.exit(1)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )

    usage = response.usage
    cost = (usage.input_tokens / 1_000_000) * 0.80 + (usage.output_tokens / 1_000_000) * 4.00
    return response.content[0].text.strip(), cost


def translate_json(input_json, language):
    """Translate all untranslated lines in an episodes/XX.json file in-place."""
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_cost = 0
    context = []

    for scene in data["scenes"]:
        for line in scene["lines"]:
            ja = line["ja"]
            if not ja:
                continue
            if line.get("en"):  # already translated
                context.append(ja)
                if len(context) > 5:
                    context.pop(0)
                continue
            print(ja)
            try:
                en, cost = translate_with_context(context, ja, language)
                total_cost += cost
                line["en"] = en
            except Exception as e:
                print(f"Error: {ja} -> {e}")
                line["en"] = ""
            context.append(ja)
            if len(context) > 5:
                context.pop(0)

    with open(input_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Total Cost: ${total_cost:.6f}")


if __name__ == "__main__":
    load_dotenv()

    if len(sys.argv) != 3:
        print("Usage: python3 translate.py episodes/XX.json en")
        sys.exit(1)

    translate_json(sys.argv[1], sys.argv[2])

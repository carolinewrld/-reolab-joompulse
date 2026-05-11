#!/usr/bin/env bash
#
# Generate the 14-shot "AO VIVO" podcast-style ad via Higgsfield Veo 3.1.
#
# Usage:
#   scripts/generate_aovivo_ad.sh <marina_start_frame> <rafael_start_frame> [outdir]
#
# Requires: `higgsfield` CLI installed and authenticated on the host running this
# script. Veo 3.1 only accepts durations 4/6/8s, so the script's source
# durations (5s/10s) are clamped to 6s/8s respectively.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <marina_image> <rafael_image> [outdir]" >&2
  exit 2
fi

MARINA="$1"
RAFAEL="$2"
OUTDIR="${3:-out/aovivo}"
mkdir -p "$OUTDIR"
LOG="$OUTDIR/urls.txt"
: > "$LOG"

MODEL="veo3_1"
ASPECT="9:16"
QUALITY="high"

SCENE_BASE="Vertical 9:16 podcast studio shot. Same dark teal chevron acoustic-panel wall as the start frame, with warm orange 'AO VIVO' neon sign glowing softly behind the speaker. Wooden round table foreground, ceramic mug on the table, monstera plant blurred in the background. Cinematic warm rim light with teal-orange split, shallow depth of field, photoreal natural skin texture, gentle handheld micro-motion. Tight medium close-up of the speaker behind the broadcast microphone."

MARINA_DESC="Late-20s mixed-race woman matching the start frame: very short buzz cut, freckles across the nose, light green eyes, small gold hoop earrings, black ribbed short-sleeve mock-neck top, black studio headphones resting around her neck. Seated behind a black RØDE broadcast mic on a boom arm."

RAFAEL_DESC="Late-30s man matching the start frame: short dark wavy hair, full dark beard with subtle grey edges, navy heather t-shirt, silver-bracelet wristwatch. Seated behind a black broadcast mic on a boom arm, hands resting on the wooden table with subtle natural gestures."

submit_shot() {
  local n="$1" img="$2" dur="$3" prompt="$4"
  printf '>>> SHOT %02d (%ss) — %s\n' "$n" "$dur" "$img"
  local shot_log="$OUTDIR/shot_$(printf '%02d' "$n").log"
  higgsfield generate create "$MODEL" \
    --start-image "$img" \
    --prompt "$prompt" \
    --aspect_ratio "$ASPECT" \
    --duration "$dur" \
    --quality "$QUALITY" \
    --wait \
    --wait-timeout 30m 2>&1 | tee "$shot_log"
  local url
  url=$(grep -Eo 'https?://[^[:space:])]+\.mp4' "$shot_log" | tail -1 || true)
  printf 'SHOT %02d %s\n' "$n" "${url:-<no-url-extracted-see-${shot_log}>}" | tee -a "$LOG"
}

submit_shot 1 "$MARINA" 6 \
"$SCENE_BASE $MARINA_DESC She leans very slightly forward with an intrigued journalist expression, eyebrows lifting on the question. She speaks one line directly to the microphone in Brazilian Portuguese with a native São Paulo accent, mid-pitch female voice, intrigued conversational pace: \"Você sabe quando seu concorrente no Mercado Livre... baixa o preço?\" Lip-sync must match the spoken line exactly."

submit_shot 2 "$RAFAEL" 6 \
"$SCENE_BASE $RAFAEL_DESC Calm confessional expression, faint reflective half-smile. He speaks slowly with a brief natural pause between the two sentences, in Brazilian Portuguese with a native São Paulo accent, mid-low pitch male voice, calm confessional tone: \"Agora eu sei... Antes eu descobria quando as vendas paravam.\" Lip-sync must match the line exactly."

submit_shot 3 "$MARINA" 6 \
"$SCENE_BASE $MARINA_DESC Curious quick reaction, slight eyebrow raise and small head tilt. She speaks one short line in Brazilian Portuguese, São Paulo accent, mid-pitch female voice, curious quick delivery: \"Como assim?\" Lip-sync exactly."

submit_shot 4 "$RAFAEL" 8 \
"$SCENE_BASE $RAFAEL_DESC Conversational pace with natural pauses, quietly building seller frustration but not theatrical, subtle hand gestures on the wooden table. He speaks the following line in Brazilian Portuguese with a native São Paulo accent, mid-low pitch male voice, delivering at a brisk pace that fits 8 seconds: \"Eu tava vendendo quarenta pedidos por dia... De repente caiu pra cinco. Fui olhar... o concorrente tinha baixado trinta por cento... três dias antes.\" Lip-sync must match the full line exactly."

submit_shot 5 "$MARINA" 6 \
"$SCENE_BASE $MARINA_DESC She leans slightly in toward the mic with a curious expression. She speaks one line in Brazilian Portuguese, São Paulo accent, mid-pitch female voice, curious leaning-in tone: \"Três dias no escuro?\" Lip-sync exactly."

submit_shot 6 "$RAFAEL" 6 \
"$SCENE_BASE $RAFAEL_DESC Quiet defeated tone, listing rhythm with short pauses between each loss. He speaks in Brazilian Portuguese, São Paulo accent, mid-low pitch male voice, quietly defeated: \"Três dias... Perdi Buy Box... perdi posição... perdi cliente.\" Lip-sync exactly."

submit_shot 7 "$MARINA" 6 \
"$SCENE_BASE $MARINA_DESC Direct curious expression, brisk delivery. She speaks in Brazilian Portuguese, São Paulo accent, mid-pitch female voice, direct curious tone: \"E como resolveu?\" Lip-sync exactly."

submit_shot 8 "$RAFAEL" 8 \
"$SCENE_BASE $RAFAEL_DESC Slight lift in energy, natural pauses between sentences, conversational rhythm, subtle hand gesture on the first sentence. He speaks the following line in Brazilian Portuguese with a native São Paulo accent, mid-low pitch male voice, at a pace that fits 8 seconds: \"Assisti um webinar do Gabriel Bollico. Ele mostrou que os sellers grandes monitoram concorrente em tempo real. Preço mudou? Sabem na hora. Estoque acabou? Na hora.\" Lip-sync must match the full line exactly."

submit_shot 9 "$MARINA" 6 \
"$SCENE_BASE $MARINA_DESC Slight disbelief expression, eyebrows up. She speaks in Brazilian Portuguese, São Paulo accent, mid-pitch female voice, slight disbelief: \"Na hora tipo minutos?\" Lip-sync exactly."

submit_shot 10 "$RAFAEL" 6 \
"$SCENE_BASE $RAFAEL_DESC Calm confident expression, deliberate pace with a clear pause between the two phrases. He speaks in Brazilian Portuguese, São Paulo accent, mid-low pitch male voice, calm and confident: \"Minutos... Não dias.\" Lip-sync exactly."

submit_shot 11 "$MARINA" 6 \
"$SCENE_BASE $MARINA_DESC Engaged softer inviting tone, warm eye contact with the camera. She speaks in Brazilian Portuguese, São Paulo accent, mid-pitch female voice, engaged and softly inviting: \"E mudou pra você?\" Lip-sync exactly."

submit_shot 12 "$RAFAEL" 8 \
"$SCENE_BASE $RAFAEL_DESC Steady delivery that builds quietly to the regret line, natural micro-pauses, softer tone on the final sentence with a small head shake on the regret. He speaks the following line in Brazilian Portuguese with a native São Paulo accent, mid-low pitch male voice, at a pace that fits 8 seconds: \"Tudo. Hoje eu recebo alerta quando qualquer concorrente muda preço. Estoque dele acabou? Eu subo o meu. É outro jogo... E eu fiquei dois anos vendendo no escuro... sem saber.\" Lip-sync must match the full line exactly."

submit_shot 13 "$MARINA" 6 \
"$SCENE_BASE $MARINA_DESC Clear direct curious tone. She speaks in Brazilian Portuguese, São Paulo accent, mid-pitch female voice, clear and direct: \"E onde aprende isso?\" Lip-sync exactly."

submit_shot 14 "$RAFAEL" 6 \
"$SCENE_BASE $RAFAEL_DESC Warm matter-of-fact tone, deliberate pace with short pauses between each phrase, slight smile, tiny finger-point downward on the closing call to action. He speaks in Brazilian Portuguese, São Paulo accent, mid-low pitch male voice, warm matter-of-fact: \"Webinar do Bollico... Gratuito. Inscreve-se... clica aqui embaixo.\" Lip-sync exactly."

echo ""
echo "Done. Per-shot URLs:"
cat "$LOG"

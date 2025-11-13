#!/bin/bash
# Monitor fine-tuning job status

source .venv/bin/activate

JOB_ID="ftjob-UntRAoBrssmmlfKjAFt4Fwdc"

echo "========================================="
echo "CocoBase AI Fine-Tuning Status Monitor"
echo "========================================="
echo "Job ID: $JOB_ID"
echo ""

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking status..."

    STATUS=$(openai api fine_tuning.jobs.retrieve -i $JOB_ID 2>&1)

    echo "$STATUS" | grep -E "(status|fine_tuned_model|trained_tokens|finished_at)" | head -10

    # Check if completed
    if echo "$STATUS" | grep -q '"status": "succeeded"'; then
        echo ""
        echo "✅ FINE-TUNING COMPLETE!"

        MODEL_ID=$(echo "$STATUS" | grep '"fine_tuned_model"' | sed 's/.*"fine_tuned_model": "\([^"]*\)".*/\1/')
        echo "🎉 New Model ID: $MODEL_ID"
        echo ""
        echo "To use this model, update your .env file:"
        echo "AI_MODEL=$MODEL_ID"
        echo ""
        echo "Or export it:"
        echo "export AI_MODEL=$MODEL_ID"
        break
    elif echo "$STATUS" | grep -q '"status": "failed"'; then
        echo ""
        echo "❌ FINE-TUNING FAILED"
        echo "$STATUS" | grep -A 3 '"error"'
        break
    fi

    echo ""
    echo "Still running... checking again in 30 seconds"
    echo "-------------------------------------------"
    sleep 30
done

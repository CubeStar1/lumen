using System;
using FloorPlanViz.Data;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>One saved plan in the library list.</summary>
    public sealed class PlanRow : MonoBehaviour
    {
        [SerializeField] Button button;
        [SerializeField] TMP_Text titleText;
        [SerializeField] TMP_Text detailText;
        [SerializeField] TMP_Text dateText;
        [SerializeField] RawImage thumbnail;
        [SerializeField] GameObject separator;

        public async void Bind(PlanSummary plan, bool last, Action onClick, Func<Awaitable<Texture2D>> loadThumbnail)
        {
            titleText.text = plan.Name;
            detailText.text = $"{Format.Summary(plan.RoomCount, plan.Area)} · {Format.Size(plan.Width, plan.Depth)}";
            dateText.text = Format.Relative(plan.UpdatedAt);
            separator.SetActive(!last);
            thumbnail.enabled = false;
            button.onClick.AddListener(() => onClick());

            if (!plan.HasImage)
                return;
            var texture = await loadThumbnail();
            if (this == null || texture == null)
                return;
            thumbnail.texture = texture;
            thumbnail.enabled = true;
            FitCover(texture);
        }

        void FitCover(Texture texture)
        {
            var aspect = (float)texture.width / texture.height;
            thumbnail.uvRect = aspect > 1f
                ? new Rect((1f - 1f / aspect) / 2f, 0f, 1f / aspect, 1f)
                : new Rect(0f, (1f - aspect) / 2f, 1f, aspect);
        }
    }
}

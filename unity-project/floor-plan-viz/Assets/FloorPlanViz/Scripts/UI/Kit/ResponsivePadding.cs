using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Widens a layout's side padding so its content never grows past a readable width.</summary>
    [RequireComponent(typeof(LayoutGroup))]
    public sealed class ResponsivePadding : MonoBehaviour
    {
        [SerializeField] float maxWidth = 680f;
        [SerializeField] int minSide = 20;

        void OnEnable() => Apply();

        void OnRectTransformDimensionsChange() => Apply();

        void Apply()
        {
            var rect = (RectTransform)transform;
            var layout = GetComponent<LayoutGroup>();
            var side = Mathf.Max(minSide, Mathf.RoundToInt((rect.rect.width - maxWidth) / 2f));
            if (layout.padding.left == side)
                return;
            layout.padding.left = layout.padding.right = side;
            LayoutRebuilder.MarkLayoutForRebuild(rect);
        }
    }
}

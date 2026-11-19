using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>An iOS segmented control: choices on a shared track with the selected one raised. On glass it uses the AR HUD's colours.</summary>
    public sealed class SegmentedControl : MonoBehaviour
    {
        [SerializeField] RectTransform track;
        [SerializeField] Button segmentTemplate;
        [SerializeField] bool onGlass;

        readonly List<(Image fill, TMP_Text label)> segments = new();

        public event Action<int> Changed;

        public int Selected { get; private set; }

        Color SelectedFill => onGlass ? Theme.GlassActive : Theme.Surface;
        Color SelectedText => Theme.Label;
        Color IdleText => onGlass ? Theme.OnGlass : Theme.Label;

        public void SetSegments(IReadOnlyList<string> labels, int selected)
        {
            segmentTemplate.gameObject.SetActive(false);
            foreach (var (fill, _) in segments)
                Destroy(fill.gameObject);
            segments.Clear();

            for (var i = 0; i < labels.Count; i++)
            {
                var button = Instantiate(segmentTemplate, track);
                button.gameObject.SetActive(true);
                var label = button.GetComponentInChildren<TMP_Text>();
                label.text = labels[i];
                var index = i;
                button.onClick.AddListener(() => Select(index, notify: true));
                segments.Add(((Image)button.targetGraphic, label));
            }
            Select(selected);
        }

        public void Select(int index, bool notify = false)
        {
            Selected = Mathf.Clamp(index, 0, Mathf.Max(0, segments.Count - 1));
            for (var i = 0; i < segments.Count; i++)
            {
                var chosen = i == Selected;
                segments[i].fill.color = chosen ? SelectedFill : Color.clear;
                segments[i].label.color = chosen ? SelectedText : IdleText;
                segments[i].label.fontWeight = chosen ? FontWeight.SemiBold : FontWeight.Regular;
            }
            if (notify)
                Changed?.Invoke(Selected);
        }
    }
}

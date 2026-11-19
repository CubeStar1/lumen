using System;
using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Api;
using FloorPlanViz.Data;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>A plan's 2D drawing, key figures, room list and the model's notes, with the way into AR. A building shows one level at a time.</summary>
    public sealed class PlanDetailScreen : AppScreen
    {
        [SerializeField] Button backButton;
        [SerializeField] Button moreButton;
        [SerializeField] TMP_Text navTitle;
        [SerializeField] TMP_Text titleText;
        [SerializeField] SegmentedControl levelPicker;
        [SerializeField] PlanOutlineGraphic outline;
        [SerializeField] TMP_Text roomsValue;
        [SerializeField] TMP_Text areaValue;
        [SerializeField] TMP_Text sizeValue;
        [SerializeField] RectTransform roomGroup;
        [SerializeField] RoomRow roomTemplate;
        [SerializeField] GameObject notesSection;
        [SerializeField] TMP_Text notesText;
        [SerializeField] Button viewButton;
        [SerializeField] ScrollRect scroll;

        public event Action BackRequested;
        public event Action MoreRequested;
        public event Action ViewRequested;

        List<LevelGeometry> levels = new();
        PlanBounds bounds;

        void Awake()
        {
            backButton.onClick.AddListener(() => BackRequested?.Invoke());
            moreButton.onClick.AddListener(() => MoreRequested?.Invoke());
            viewButton.onClick.AddListener(() => ViewRequested?.Invoke());
            roomTemplate.gameObject.SetActive(false);
            levelPicker.Changed += ShowLevel;
        }

        public void Show(PlanDocument document)
        {
            var geometry = document.Plan.Geometry;
            var size = geometry.Bounds.Size;
            levels = geometry.Levels.OrderBy(l => l.Elevation).ToList();
            bounds = geometry.Bounds;

            SetName(document.Name);
            moreButton.gameObject.SetActive(document.IsSaved);
            levelPicker.gameObject.SetActive(levels.Count > 1);
            levelPicker.SetSegments(levels.Select(l => Format.LevelLabel(l.Name)).ToList(), 0);
            sizeValue.text = Format.Size(size.x, size.y);
            ShowLevel(0);
            ShowNotes(document);
            scroll.verticalNormalizedPosition = 1f;
        }

        public void SetName(string name) => navTitle.text = titleText.text = name;

        void ShowLevel(int index)
        {
            var level = levels[index];
            var indoor = level.Rooms.Where(r => !r.Outdoor).ToList();
            outline.SetGeometry(level, bounds);
            roomsValue.text = indoor.Count.ToString();
            areaValue.text = Format.Area(indoor.Sum(r => r.Area));
            ShowRooms(level);
        }

        void ShowRooms(LevelGeometry level)
        {
            foreach (Transform child in roomGroup)
            {
                if (child != roomTemplate.transform)
                    Destroy(child.gameObject);
            }

            var rooms = level.Rooms.OrderByDescending(r => r.Area).ToList();
            for (var i = 0; i < rooms.Count; i++)
            {
                var row = Instantiate(roomTemplate, roomGroup);
                row.gameObject.SetActive(true);
                row.Bind(rooms[i], i == rooms.Count - 1);
            }
        }

        void ShowNotes(PlanDocument document)
        {
            var warnings = document.Plan.Warnings.Select(w => $"<color=#FF9500><b>Check:</b></color> {w}");
            var lines = PlanJson.Notes(document.Plan).Concat(warnings).Where(l => !string.IsNullOrWhiteSpace(l)).ToList();
            notesSection.SetActive(lines.Count > 0);
            notesText.text = string.Join("\n\n", lines);
        }
    }
}

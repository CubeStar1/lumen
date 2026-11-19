using System;
using System.Linq;
using FloorPlanViz.Api;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>A plan's 2D drawing, key figures, room list and the model's notes, with the way into AR.</summary>
    public sealed class PlanDetailScreen : AppScreen
    {
        [SerializeField] Button backButton;
        [SerializeField] Button moreButton;
        [SerializeField] TMP_Text navTitle;
        [SerializeField] TMP_Text titleText;
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

        void Awake()
        {
            backButton.onClick.AddListener(() => BackRequested?.Invoke());
            moreButton.onClick.AddListener(() => MoreRequested?.Invoke());
            viewButton.onClick.AddListener(() => ViewRequested?.Invoke());
            roomTemplate.gameObject.SetActive(false);
        }

        public void Show(PlanDocument document)
        {
            var geometry = document.Plan.Geometry;
            var size = geometry.Bounds.Size;

            SetName(document.Name);
            moreButton.gameObject.SetActive(document.IsSaved);
            outline.SetGeometry(geometry.Ground, geometry.Bounds);
            roomsValue.text = geometry.Rooms.Count(r => !r.Outdoor).ToString();
            areaValue.text = Format.Area(geometry.Rooms.Where(r => !r.Outdoor).Sum(r => r.Area));
            sizeValue.text = Format.Size(size.x, size.y);
            ShowRooms(document);
            ShowNotes(document);
            scroll.verticalNormalizedPosition = 1f;
        }

        public void SetName(string name) => navTitle.text = titleText.text = name;

        void ShowRooms(PlanDocument document)
        {
            foreach (Transform child in roomGroup)
            {
                if (child != roomTemplate.transform)
                    Destroy(child.gameObject);
            }

            var rooms = document.Plan.Geometry.Rooms.OrderByDescending(r => r.Area).ToList();
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

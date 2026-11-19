using FloorPlanViz.UI;
using TMPro;
using UnityEngine;
using static FloorPlanViz.Editor.UiKit;

namespace FloorPlanViz.Editor
{
    static class DetailBuilder
    {
        const float NavHeight = 50f;
        const float BottomBarHeight = 78f;

        public static PlanDetailScreen Build(Transform root)
        {
            var screen = Page<PlanDetailScreen>("PlanDetail", root);
            var (scroll, content) = Scroll("Scroll", screen.transform, Pad(20, 20, 4, 24), 12f, LibraryBuilder.MaxWidth);
            Stretch((RectTransform)scroll.transform, top: NavHeight, bottom: BottomBarHeight);

            var title = Label("Title", content, "Plan", TextStyle.Title1, Theme.Label);
            title.margin = new Vector4(0f, 0f, 0f, 4f);

            var planCard = Card("PlanCard", content, 16f);
            Size(planCard, height: 300f);
            var outline = Stretch(Node("Outline", planCard), 14f, 14f, 14f, 14f).gameObject.AddComponent<PlanOutlineGraphic>();
            outline.raycastTarget = false;

            var stats = Node("Stats", content);
            Row(stats, Pad(0), 10f, TextAnchor.MiddleLeft, expand: true);
            var rooms = Stat(stats, "Rooms");
            var area = Stat(stats, "Floor area");
            var size = Stat(stats, "Footprint");

            var roomsSection = Node("RoomsSection", content);
            Column(roomsSection, Pad(0), 0f);
            SectionHeader(roomsSection, "Rooms");
            var roomList = Card("RoomList", roomsSection, clip: true);
            Column(roomList, Pad(0), 0f);
            var roomRow = BuildRoomRow(roomList);

            var notesSection = Node("NotesSection", content);
            Column(notesSection, Pad(0), 0f);
            SectionHeader(notesSection, "Notes from the model");
            var notesCard = Card("NotesCard", notesSection);
            Column(notesCard, Pad(16, 16, 14, 14), 0f);
            var notes = Label("Notes", notesCard, "", TextStyle.Subhead, Theme.SecondaryLabel);

            var (back, more, navTitle) = NavBar(screen.transform, scroll);
            var view = BottomBar(screen.transform);

            SerializedWiring.Set(screen, "backButton", back);
            SerializedWiring.Set(screen, "moreButton", more);
            SerializedWiring.Set(screen, "navTitle", navTitle);
            SerializedWiring.Set(screen, "titleText", title);
            SerializedWiring.Set(screen, "outline", outline);
            SerializedWiring.Set(screen, "roomsValue", rooms);
            SerializedWiring.Set(screen, "areaValue", area);
            SerializedWiring.Set(screen, "sizeValue", size);
            SerializedWiring.Set(screen, "roomGroup", roomList);
            SerializedWiring.Set(screen, "roomTemplate", roomRow);
            SerializedWiring.Set(screen, "notesSection", notesSection.gameObject);
            SerializedWiring.Set(screen, "notesText", notes);
            SerializedWiring.Set(screen, "viewButton", view);
            SerializedWiring.Set(screen, "scroll", scroll);
            return screen;
        }

        static TMP_Text Stat(Transform parent, string caption)
        {
            var tile = Card(caption, parent);
            Size(tile, width: 0f, flexibleWidth: 1f);
            Column(tile, Pad(14, 10, 12, 12), 2f);
            var value = Label("Value", tile, "–", TextStyle.Title3, Theme.Label, wrap: false);
            Label("Caption", tile, caption, TextStyle.Footnote, Theme.SecondaryLabel, wrap: false);
            return value;
        }

        static RoomRow BuildRoomRow(Transform parent)
        {
            var rect = Node("RoomRow", parent);
            Size(rect, height: 56f);
            Fill(rect, Theme.Surface);
            Row(rect, Pad(14, 16, 0, 0), 12f);

            var badge = Node("Badge", rect);
            Size(badge, width: 32f, height: 32f);
            var badgeFill = Fill(badge, Theme.Fill, 8f);
            var icon = Icon("Icon", badge, Icons.Category, 19f, new Color(0f, 0f, 0f, 0.6f));
            Stretch(icon.rectTransform);

            var copy = Node("Copy", rect);
            Size(copy, width: 0f, flexibleWidth: 1f);
            Column(copy, Pad(0), 0f, TextAnchor.MiddleLeft);
            var name = Label("Name", copy, "Room", TextStyle.Body, Theme.Label, wrap: false);
            var type = Label("Type", copy, "", TextStyle.Footnote, Theme.SecondaryLabel, wrap: false);
            var area = Label("Area", rect, "", TextStyle.Body, Theme.SecondaryLabel, TextAlignmentOptions.Right, wrap: false);
            var separator = BottomSeparator(rect, 14f + 32f + 12f);

            var row = rect.gameObject.AddComponent<RoomRow>();
            SerializedWiring.Set(row, "iconBackground", badgeFill);
            SerializedWiring.Set(row, "iconText", icon);
            SerializedWiring.Set(row, "nameText", name);
            SerializedWiring.Set(row, "typeText", type);
            SerializedWiring.Set(row, "areaText", area);
            SerializedWiring.Set(row, "separator", separator);
            return row;
        }

        static (UnityEngine.UI.Button back, UnityEngine.UI.Button more, TMP_Text title) NavBar(Transform parent, UnityEngine.UI.ScrollRect scroll)
        {
            var bar = Place(Node("NavBar", parent), Vector2.up, Vector2.one, new Vector2(0.5f, 1f), Vector2.zero, new Vector2(0f, NavHeight));
            Fill(bar, Theme.Background.WithAlpha(0.96f)).raycastTarget = true;

            var back = TextButton("BackButton", bar, "Plans", ButtonStyle.Plain, Icons.ChevronLeft, NavHeight, 0f);
            back.GetComponent<UnityEngine.UI.Image>().color = Color.clear;
            back.gameObject.AddComponent<PressFeedback>();
            var backRect = (RectTransform)back.transform;
            Place(backRect, Vector2.zero, Vector2.up, Vector2.zero, Vector2.zero, new Vector2(110f, 0f));
            var backContent = backRect.Find("Content").GetComponent<UnityEngine.UI.HorizontalLayoutGroup>();
            backContent.padding = Pad(6, 0, 0, 0);
            backContent.spacing = 0f;
            backContent.childAlignment = TextAnchor.MiddleLeft;
            backRect.Find("Content/Icon").GetComponent<TMP_Text>().fontSize = 30f;

            var more = IconButton("MoreButton", bar, Icons.MoreHoriz, 30f, 22f, Theme.Accent, Theme.AccentTint);
            Place((RectTransform)more.transform, new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(-16f, 0f), Vector2.one * 30f);

            var fading = Stretch(Node("Fading", bar));
            var group = fading.gameObject.AddComponent<CanvasGroup>();
            group.blocksRaycasts = false;
            var title = Label("Title", fading, "", TextStyle.Headline, Theme.Label, TextAlignmentOptions.Center, wrap: false);
            Stretch(title.rectTransform, 120f, 0f, 120f, 0f);
            BottomSeparator(fading, 0f);

            var fade = bar.gameObject.AddComponent<ScrollFadeIn>();
            SerializedWiring.Set(fade, "scroll", scroll);
            SerializedWiring.Set(fade, "target", group);
            return (back, more, title);
        }

        static UnityEngine.UI.Button BottomBar(Transform parent)
        {
            var bar = Place(Node("BottomBar", parent), Vector2.zero, Vector2.right, new Vector2(0.5f, 0f), Vector2.zero, new Vector2(0f, BottomBarHeight));
            Fill(bar, Theme.Background.WithAlpha(0.96f)).raycastTarget = true;
            var column = Stretch(Node("Column", bar));
            Column(column, Pad(20, 20, 12, 16), 0f, TextAnchor.UpperCenter);
            Responsive(column, LibraryBuilder.MaxWidth, 20);
            Fill(Place(Node("Separator", bar), Vector2.up, Vector2.one, new Vector2(0.5f, 1f), Vector2.zero, new Vector2(0f, Hairline)), Theme.Separator);
            return TextButton("ViewButton", column, "View in AR", ButtonStyle.Filled, Icons.ViewInAr);
        }
    }
}

using FloorPlanViz.UI;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using static FloorPlanViz.Editor.UiKit;

namespace FloorPlanViz.Editor
{
    static class LibraryBuilder
    {
        public const float MaxWidth = 680f;
        const float RowHeight = 76f;
        const float Thumbnail = 56f;

        public static LibraryScreen Build(Transform root)
        {
            var screen = Page<LibraryScreen>("Library", root);
            var (scroll, content) = Scroll("Scroll", screen.transform, Pad(20, 20, 4, 40), 0f, MaxWidth);

            var bar = Node("TopBar", content);
            Size(bar, height: 44f);
            var settings = IconButton("SettingsButton", bar, Icons.Settings, 40f, 26f, Theme.Accent, Color.clear);
            Place((RectTransform)settings.transform, new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(6f, 0f), Vector2.one * 40f);

            Label("Title", content, "Floor Plans", TextStyle.LargeTitle, Theme.Label, wrap: false);
            var (connectionButton, badge) = Connection(content);
            Spacer(content, 20f);

            var (newPlan, sample) = StartCard(content);
            Spacer(content, 12f);

            var (refresh, loading) = ListHeader(content);
            var list = Card("PlanList", content, clip: true);
            Column(list, Pad(0), 0f);
            var row = BuildRow(list);

            var message = Card("Message", content);
            Column(message, Pad(28, 28, 28, 28), 6f, TextAnchor.MiddleCenter).childForceExpandWidth = true;
            Icon("Icon", message, Icons.Apartment, 40f, Theme.TertiaryLabel);
            var messageTitle = Label("Title", message, "No plans yet", TextStyle.Headline, Theme.Label, TextAlignmentOptions.Center);
            var messageDetail = Label("Detail", message, "", TextStyle.Subhead, Theme.SecondaryLabel, TextAlignmentOptions.Center);

            list.gameObject.SetActive(false);
            message.gameObject.SetActive(false);

            SerializedWiring.Set(screen, "settingsButton", settings);
            SerializedWiring.Set(screen, "connectionButton", connectionButton);
            SerializedWiring.Set(screen, "connection", badge);
            SerializedWiring.Set(screen, "newPlanButton", newPlan);
            SerializedWiring.Set(screen, "sampleButton", sample);
            SerializedWiring.Set(screen, "refreshButton", refresh);
            SerializedWiring.Set(screen, "listGroup", list);
            SerializedWiring.Set(screen, "rowTemplate", row);
            SerializedWiring.Set(screen, "listCard", list.gameObject);
            SerializedWiring.Set(screen, "messageCard", message.gameObject);
            SerializedWiring.Set(screen, "messageTitle", messageTitle);
            SerializedWiring.Set(screen, "messageDetail", messageDetail);
            SerializedWiring.Set(screen, "loadingIndicator", loading);
            SerializedWiring.Set(screen, "scroll", scroll);
            return screen;
        }

        public static (Button button, ConnectionBadge badge) Connection(Transform parent)
        {
            var rect = Node("Connection", parent);
            Size(rect, height: 26f);
            var hit = rect.gameObject.AddComponent<Image>();
            hit.color = Color.clear;
            var button = Pressable(rect, hit, 0.6f);
            Row(rect, Pad(0), 7f);
            var dot = Circle("Dot", rect, 8f, Theme.TertiaryLabel);
            var label = Label("Label", rect, "Connecting…", TextStyle.Footnote, Theme.SecondaryLabel, wrap: false);
            var badge = rect.gameObject.AddComponent<ConnectionBadge>();
            SerializedWiring.Set(badge, "dot", dot);
            SerializedWiring.Set(badge, "label", label);
            return (button, badge);
        }

        static (Button newPlan, Button sample) StartCard(Transform parent)
        {
            var card = Card("StartCard", parent, 16f);
            Column(card, Pad(16, 16, 18, 16), 14f);

            var header = Node("Header", card);
            Row(header, Pad(0), 14f, TextAnchor.MiddleLeft);
            var badge = Node("Badge", header);
            Size(badge, width: 52f, height: 52f);
            Fill(badge, Theme.AccentTint, 14f);
            Stretch(Icon("Icon", badge, Icons.ViewInAr, 28f, Theme.Accent).rectTransform);

            var copy = Node("Copy", header);
            Size(copy, width: 0f, flexibleWidth: 1f);
            Column(copy, Pad(0), 2f, TextAnchor.MiddleLeft);
            Label("Title", copy, "Turn a floor plan into 3D", TextStyle.Headline, Theme.Label);
            Label("Detail", copy, "Choose a photo or scan of a 2D plan, then place the model in your room.",
                TextStyle.Subhead, Theme.SecondaryLabel);

            var newPlan = TextButton("NewPlanButton", card, "Choose a photo", ButtonStyle.Filled, Icons.AddPhoto);
            var sample = TextButton("SampleButton", card, "Try the sample plan", ButtonStyle.Tinted, Icons.Science);
            return (newPlan, sample);
        }

        static (Button refresh, GameObject loading) ListHeader(Transform parent)
        {
            var row = Node("ListHeader", parent);
            Row(row, Pad(16, 4, 20, 6), 6f, TextAnchor.LowerLeft);
            var title = Label("Title", row, "RECENT PLANS", TextStyle.Footnote, Theme.SecondaryLabel, wrap: false);
            Size(title, width: 0f, flexibleWidth: 1f);
            var loading = ActivityIndicator("Loading", row, 18f, Theme.SecondaryLabel);
            var refresh = IconButton("RefreshButton", row, Icons.Refresh, 28f, 20f, Theme.Accent, Color.clear);
            return (refresh, loading.gameObject);
        }

        static PlanRow BuildRow(Transform parent)
        {
            var rect = Node("PlanRow", parent);
            Size(rect, height: RowHeight);
            var background = Fill(rect, Theme.Surface);
            var button = Pressable(rect, background);
            Row(rect, Pad(16, 12, 6, 6), 12f);

            var frame = Node("Thumbnail", rect);
            Size(frame, width: Thumbnail, height: Thumbnail);
            Fill(frame, Theme.Fill, 10f);
            frame.gameObject.AddComponent<Mask>();
            Stretch(Icon("Placeholder", frame, Icons.Apartment, 26f, Theme.TertiaryLabel).rectTransform);
            var picture = Stretch(Node("Picture", frame)).gameObject.AddComponent<RawImage>();
            picture.raycastTarget = false;

            var copy = Node("Copy", rect);
            Size(copy, width: 0f, flexibleWidth: 1f);
            Column(copy, Pad(0), 1f, TextAnchor.MiddleLeft);
            var title = Label("Title", copy, "Plan", TextStyle.Headline, Theme.Label, wrap: false);
            var detail = Label("Detail", copy, "", TextStyle.Subhead, Theme.SecondaryLabel, wrap: false);
            var date = Label("Date", copy, "", TextStyle.Footnote, Theme.SecondaryLabel, wrap: false);

            Icon("Chevron", rect, Icons.ChevronRight, 22f, Theme.TertiaryLabel);
            var separator = BottomSeparator(rect, 16f + Thumbnail + 12f);

            var row = rect.gameObject.AddComponent<PlanRow>();
            SerializedWiring.Set(row, "button", button);
            SerializedWiring.Set(row, "titleText", title);
            SerializedWiring.Set(row, "detailText", detail);
            SerializedWiring.Set(row, "dateText", date);
            SerializedWiring.Set(row, "thumbnail", picture);
            SerializedWiring.Set(row, "separator", separator);
            return row;
        }
    }
}

using FloorPlanViz.UI;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using static FloorPlanViz.Editor.UiKit;

namespace FloorPlanViz.Editor
{
    static class HudBuilder
    {
        public static ArHud Build(Transform root)
        {
            var hud = Page<ArHud>("ArHud", root);
            var rect = (RectTransform)hud.transform;

            var close = IconButton("CloseButton", rect, Icons.Close, 44f, 24f, Theme.OnGlass, Theme.Glass);
            Place((RectTransform)close.transform, Vector2.up, Vector2.up, Vector2.up, new Vector2(16f, -8f), Vector2.one * 44f);

            var (titlePill, title) = Pill("TitlePill", rect, TextStyle.Headline, new Vector2(0f, -8f), 44f, 22f);
            title.text = "Plan";
            var (hintPill, hint) = Pill("HintPill", rect, TextStyle.Subhead, new Vector2(0f, -62f), -1f, 18f);
            hint.textWrappingMode = TextWrappingModes.Normal;

            var placing = Place(Node("PlacingControls", rect), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 28f), new Vector2(200f, 56f));
            var placeGroup = placing.gameObject.AddComponent<CanvasGroup>();
            var place = TextButton("PlaceButton", placing, "Place model", ButtonStyle.Light, Icons.ViewInAr, 56f, 28f);
            Stretch((RectTransform)place.transform);
            DropShadow((RectTransform)place.transform, 10f, 0.25f);

            var toolbar = Place(Node("Toolbar", rect), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 20f), Vector2.zero);
            Fill(toolbar, Theme.Glass, 30f).raycastTarget = true;
            Row(toolbar, Pad(10, 10, 9, 7), 2f, TextAnchor.MiddleCenter);
            FitContent(toolbar, horizontal: true, vertical: true);
            var roof = BuildToolbarButton(toolbar, "Roof");
            var labels = BuildToolbarButton(toolbar, "Labels");
            var mode = BuildToolbarButton(toolbar, "Mode");
            var reset = BuildToolbarButton(toolbar, "Reset");
            var edit = BuildToolbarButton(toolbar, "Edit");

            SerializedWiring.Set(hud, "closeButton", close);
            SerializedWiring.Set(hud, "titleText", title);
            SerializedWiring.Set(hud, "hintPill", hintPill);
            SerializedWiring.Set(hud, "hintText", hint);
            SerializedWiring.Set(hud, "placingControls", placing.gameObject);
            SerializedWiring.Set(hud, "placeButton", place);
            SerializedWiring.Set(hud, "placeGroup", placeGroup);
            SerializedWiring.Set(hud, "toolbar", toolbar.gameObject);
            SerializedWiring.Set(hud, "roofButton", roof);
            SerializedWiring.Set(hud, "labelsButton", labels);
            SerializedWiring.Set(hud, "modeButton", mode);
            SerializedWiring.Set(hud, "resetButton", reset);
            SerializedWiring.Set(hud, "editButton", edit);
            return hud;
        }

        /// <summary>A dark glass capsule, centred at the top, that sizes itself to its text.</summary>
        static (GameObject pill, TMP_Text text) Pill(string name, RectTransform parent, TextStyle style, Vector2 position, float height, float radius)
        {
            var pill = Place(Node(name, parent), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), position, Vector2.zero);
            Fill(pill, Theme.Glass, radius);
            Row(pill, height > 0f ? Pad(18, 18, 0, 0) : Pad(16, 16, 9, 9), 0f, TextAnchor.MiddleCenter);
            FitContent(pill, horizontal: true, vertical: height <= 0f);
            if (height > 0f)
                pill.sizeDelta = new Vector2(0f, height);

            var text = Label("Text", pill, "", style, Theme.OnGlass, TextAlignmentOptions.Center, wrap: false);
            Size(text).maxWidth = 320f;
            return (pill.gameObject, text);
        }

        static ToolbarButton BuildToolbarButton(Transform parent, string name)
        {
            var rect = Node(name, parent);
            Size(rect, width: 62f, height: 64f);
            var disc = Place(Node("Disc", rect), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), Vector2.zero, Vector2.one * 44f);
            var discImage = Fill(disc, Color.white.WithAlpha(0.18f), 22f);
            var button = Pressable(rect, discImage, 0.7f);
            rect.gameObject.AddComponent<PressFeedback>();
            var icon = Icon("Icon", disc, Icons.Label, 23f, Theme.OnGlass);
            Stretch(icon.rectTransform);
            var caption = Label("Caption", rect, name, TextStyle.Caption, Theme.OnGlass, TextAlignmentOptions.Center, wrap: false);
            Place(caption.rectTransform, Vector2.zero, Vector2.right, new Vector2(0.5f, 0f), Vector2.zero, new Vector2(0f, 16f));

            var item = rect.gameObject.AddComponent<ToolbarButton>();
            SerializedWiring.Set(item, "button", button);
            SerializedWiring.Set(item, "disc", discImage);
            SerializedWiring.Set(item, "iconText", icon);
            SerializedWiring.Set(item, "captionText", caption);
            return item;
        }
    }
}

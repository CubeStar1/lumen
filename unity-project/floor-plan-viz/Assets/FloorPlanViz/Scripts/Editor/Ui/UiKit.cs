using FloorPlanViz.UI;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.Editor
{
    enum TextStyle
    {
        LargeTitle,
        Title1,
        Title3,
        Headline,
        Body,
        Subhead,
        Footnote,
        Caption,
    }

    enum ButtonStyle
    {
        Filled,
        Tinted,
        Gray,
        Plain,
        Light,
    }

    /// <summary>Builds uGUI elements in iOS style. Sizes are in points; the canvas scales them per device.</summary>
    static class UiKit
    {
        public const float Hairline = 0.66f;

        /// <summary>Inter's line height as a multiple of font size. Ellipsis text renders nothing if its box is shorter.</summary>
        const float LineHeight = 1.22f;

        static UiAssets assets;

        public static void Use(UiAssets value) => assets = value;

        public static RectTransform Node(string name, Transform parent)
        {
            var rect = new GameObject(name, typeof(RectTransform)).GetComponent<RectTransform>();
            rect.SetParent(parent, false);
            return rect;
        }

        public static RectTransform Stretch(RectTransform rect, float left = 0f, float bottom = 0f, float right = 0f, float top = 0f)
        {
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = new Vector2(left, bottom);
            rect.offsetMax = new Vector2(-right, -top);
            return rect;
        }

        /// <summary>Anchors to a point (or a span when min and max differ) with a pivot, offset and size.</summary>
        public static RectTransform Place(RectTransform rect, Vector2 anchorMin, Vector2 anchorMax, Vector2 pivot, Vector2 position, Vector2 size)
        {
            rect.anchorMin = anchorMin;
            rect.anchorMax = anchorMax;
            rect.pivot = pivot;
            rect.anchoredPosition = position;
            rect.sizeDelta = size;
            return rect;
        }

        public static RectOffset Pad(int left, int right, int top, int bottom) => new(left, right, top, bottom);

        public static RectOffset Pad(int all) => new(all, all, all, all);

        public static VerticalLayoutGroup Column(Component host, RectOffset padding, float spacing, TextAnchor alignment = TextAnchor.UpperLeft)
        {
            var layout = host.gameObject.AddComponent<VerticalLayoutGroup>();
            layout.padding = padding;
            layout.spacing = spacing;
            layout.childAlignment = alignment;
            layout.childControlWidth = layout.childControlHeight = true;
            layout.childForceExpandWidth = true;
            layout.childForceExpandHeight = false;
            return layout;
        }

        public static HorizontalLayoutGroup Row(Component host, RectOffset padding, float spacing, TextAnchor alignment = TextAnchor.MiddleLeft, bool expand = false)
        {
            var layout = host.gameObject.AddComponent<HorizontalLayoutGroup>();
            layout.padding = padding;
            layout.spacing = spacing;
            layout.childAlignment = alignment;
            layout.childControlWidth = layout.childControlHeight = true;
            layout.childForceExpandWidth = expand;
            layout.childForceExpandHeight = false;
            return layout;
        }

        /// <summary>Sets the layout sizes that are given (non-negative) and leaves the rest unchanged.</summary>
        public static LayoutElement Size(Component target, float width = -1f, float height = -1f, float flexibleWidth = -1f, float flexibleHeight = -1f)
        {
            if (!target.TryGetComponent<LayoutElement>(out var element))
                element = target.gameObject.AddComponent<LayoutElement>();
            if (width >= 0f)
                element.preferredWidth = element.minWidth = width;
            if (height >= 0f)
                element.preferredHeight = element.minHeight = height;
            if (flexibleWidth >= 0f)
                element.flexibleWidth = flexibleWidth;
            if (flexibleHeight >= 0f)
                element.flexibleHeight = flexibleHeight;
            return element;
        }

        public static void FitContent(Component target, bool horizontal, bool vertical)
        {
            var fitter = target.gameObject.AddComponent<ContentSizeFitter>();
            fitter.horizontalFit = horizontal ? ContentSizeFitter.FitMode.PreferredSize : ContentSizeFitter.FitMode.Unconstrained;
            fitter.verticalFit = vertical ? ContentSizeFitter.FitMode.PreferredSize : ContentSizeFitter.FitMode.Unconstrained;
        }

        public static RectTransform Spacer(Transform parent, float height = -1f, bool flexible = false)
        {
            var rect = Node("Spacer", parent);
            Size(rect, height: height, flexibleWidth: flexible ? 1f : -1f, flexibleHeight: flexible ? 1f : -1f);
            return rect;
        }

        public static Image Fill(Component target, Color colour, float radius = 0f)
        {
            var image = target.gameObject.AddComponent<ShapeImage>();
            image.color = colour;
            image.raycastTarget = false;
            if (radius > 0f)
            {
                image.sprite = assets.Rounded;
                image.type = Image.Type.Sliced;
                image.pixelsPerUnitMultiplier = UiAssets.RoundedBorder / radius;
            }
            return image;
        }

        public static RectTransform Card(string name, Transform parent, float radius = 14f, Color? colour = null, bool clip = false)
        {
            var rect = Node(name, parent);
            Fill(rect, colour ?? Theme.Surface, radius);
            if (clip)
                rect.gameObject.AddComponent<Mask>();
            return rect;
        }

        public static void DropShadow(RectTransform target, float spread = 14f, float opacity = 0.16f)
        {
            var shadow = Node("Shadow", target);
            shadow.SetAsFirstSibling();
            Stretch(shadow, -spread, -spread - 4f, -spread, -spread + 4f);
            shadow.gameObject.AddComponent<LayoutElement>().ignoreLayout = true;
            var image = shadow.gameObject.AddComponent<Image>();
            image.sprite = assets.Shadow;
            image.type = Image.Type.Sliced;
            image.color = new Color(0f, 0f, 0f, opacity);
            image.raycastTarget = false;
        }

        public static TMP_Text Label(string name, Transform parent, string content, TextStyle style, Color colour,
            TextAlignmentOptions alignment = TextAlignmentOptions.Left, bool wrap = true)
        {
            var text = Node(name, parent).gameObject.AddComponent<TextMeshProUGUI>();
            text.font = assets.Font;
            text.text = content;
            text.color = colour;
            text.alignment = alignment;
            text.raycastTarget = false;
            text.textWrappingMode = wrap ? TextWrappingModes.Normal : TextWrappingModes.NoWrap;
            text.overflowMode = wrap ? TextOverflowModes.Overflow : TextOverflowModes.Ellipsis;
            (text.fontSize, text.fontWeight, text.characterSpacing) = style switch
            {
                TextStyle.LargeTitle => (34f, FontWeight.Bold, -1.6f),
                TextStyle.Title1 => (28f, FontWeight.Bold, -1.2f),
                TextStyle.Title3 => (20f, FontWeight.SemiBold, -0.8f),
                TextStyle.Headline => (17f, FontWeight.SemiBold, -0.6f),
                TextStyle.Body => (17f, FontWeight.Regular, -0.6f),
                TextStyle.Subhead => (15f, FontWeight.Regular, -0.4f),
                TextStyle.Footnote => (13f, FontWeight.Regular, -0.2f),
                _ => (11f, FontWeight.Medium, 0f),
            };
            if (!wrap)
                text.gameObject.AddComponent<LayoutElement>().minHeight = Mathf.Ceil(text.fontSize * LineHeight);
            return text;
        }

        public static TMP_Text Icon(string name, Transform parent, string glyph, float size, Color colour)
        {
            var text = Node(name, parent).gameObject.AddComponent<TextMeshProUGUI>();
            text.font = assets.IconFont;
            text.text = glyph;
            text.fontSize = size;
            text.color = colour;
            text.alignment = TextAlignmentOptions.Center;
            text.textWrappingMode = TextWrappingModes.NoWrap;
            text.raycastTarget = false;
            Size(text, width: size, height: size);
            return text;
        }

        public static TMP_Text SectionHeader(Transform parent, string title)
        {
            var text = Label("Header", parent, title.ToUpperInvariant(), TextStyle.Footnote, Theme.SecondaryLabel);
            text.margin = new Vector4(16f, 22f, 16f, 6f);
            return text;
        }

        public static Image Separator(Transform parent, float inset = 0f)
        {
            var rect = Node("Separator", parent);
            Size(rect, height: Hairline);
            var line = Node("Line", rect);
            Stretch(line, left: inset);
            return Fill(line, Theme.Separator);
        }

        /// <summary>A hairline along the bottom edge that takes no part in layout.</summary>
        public static GameObject BottomSeparator(RectTransform parent, float inset)
        {
            var rect = Node("Separator", parent);
            rect.gameObject.AddComponent<LayoutElement>().ignoreLayout = true;
            Place(rect, Vector2.zero, Vector2.right, new Vector2(0.5f, 0f), new Vector2(inset / 2f, 0f), new Vector2(-inset, Hairline));
            Fill(rect, Theme.Separator);
            return rect.gameObject;
        }

        public static Button Pressable(Component target, Graphic graphic, float pressed = 0.88f)
        {
            graphic.raycastTarget = true;
            var button = target.gameObject.AddComponent<Button>();
            button.targetGraphic = graphic;
            var colours = button.colors;
            colours.normalColor = colours.highlightedColor = colours.selectedColor = Color.white;
            colours.pressedColor = new Color(pressed, pressed, pressed, 1f);
            colours.disabledColor = new Color(1f, 1f, 1f, 0.45f);
            colours.fadeDuration = 0.08f;
            button.colors = colours;
            button.navigation = new Navigation { mode = Navigation.Mode.None };
            return button;
        }

        public static Button TextButton(string name, Transform parent, string label, ButtonStyle style, string icon = null,
            float height = 50f, float radius = 14f)
        {
            var rect = Node(name, parent);
            Size(rect, height: height);
            var (background, foreground, weight) = style switch
            {
                ButtonStyle.Filled => (Theme.Accent, Color.white, FontWeight.SemiBold),
                ButtonStyle.Tinted => (Theme.AccentTint, Theme.Accent, FontWeight.SemiBold),
                ButtonStyle.Gray => (Theme.Fill, Theme.Label, FontWeight.SemiBold),
                ButtonStyle.Light => (Theme.GlassActive, Theme.Label, FontWeight.SemiBold),
                _ => (Color.clear, Theme.Accent, FontWeight.Regular),
            };
            var image = Fill(rect, background, radius);
            var button = Pressable(rect, image, 0.85f);
            if (style == ButtonStyle.Plain)
                HighlightOnPress(button, image);
            else
                rect.gameObject.AddComponent<PressFeedback>();

            var content = Node("Content", rect);
            Stretch(content);
            Row(content, Pad(16, 16, 0, 0), 8f, TextAnchor.MiddleCenter);
            if (icon != null)
                Icon("Icon", content, icon, 21f, foreground);
            var text = Label("Label", content, label, TextStyle.Headline, foreground, TextAlignmentOptions.Center, wrap: false);
            text.fontWeight = weight;
            return button;
        }

        /// <summary>An invisible background that shows a light grey wash while pressed, like a table cell.</summary>
        static void HighlightOnPress(Button button, Image background)
        {
            background.color = new Color(0f, 0f, 0f, 0.08f);
            var colours = button.colors;
            colours.normalColor = colours.highlightedColor = colours.selectedColor = colours.disabledColor = new Color(1f, 1f, 1f, 0f);
            colours.pressedColor = Color.white;
            button.colors = colours;
        }

        public static Button IconButton(string name, Transform parent, string glyph, float size, float iconSize, Color iconColour, Color background)
        {
            var rect = Node(name, parent);
            Size(rect, width: size, height: size);
            rect.sizeDelta = Vector2.one * size;
            var image = Fill(rect, background, size / 2f);
            var button = Pressable(rect, image, 0.6f);
            rect.gameObject.AddComponent<PressFeedback>();
            var icon = Icon("Icon", rect, glyph, iconSize, iconColour);
            Stretch(icon.rectTransform);
            return button;
        }

        public static TMP_InputField TextField(string name, Transform parent, string placeholder, bool multiline, float height, float radius = 10f)
        {
            var rect = Node(name, parent);
            Size(rect, height: height);
            var image = Fill(rect, Theme.Fill, radius);
            image.raycastTarget = true;

            var viewport = Stretch(Node("Text Area", rect), 12f, 8f, 12f, 8f);
            viewport.gameObject.AddComponent<RectMask2D>();
            var alignment = multiline ? TextAlignmentOptions.TopLeft : TextAlignmentOptions.Left;
            var hint = Label("Placeholder", viewport, placeholder, TextStyle.Body, Theme.SecondaryLabel, alignment, wrap: multiline);
            var value = Label("Text", viewport, "", TextStyle.Body, Theme.Label, alignment, wrap: multiline);
            Stretch(hint.rectTransform);
            Stretch(value.rectTransform);

            var field = rect.gameObject.AddComponent<TMP_InputField>();
            field.textViewport = viewport;
            field.textComponent = value;
            field.placeholder = hint;
            field.targetGraphic = image;
            field.fontAsset = assets.Font;
            field.pointSize = 17f;
            field.caretColor = Theme.Accent;
            field.customCaretColor = true;
            field.caretWidth = 2;
            field.selectionColor = Theme.AccentTint;
            field.lineType = multiline ? TMP_InputField.LineType.MultiLineNewline : TMP_InputField.LineType.SingleLine;
            field.navigation = new Navigation { mode = Navigation.Mode.None };
            return field;
        }

        /// <summary>A vertical scroll view whose content column is padded to stay readable on wide screens.</summary>
        public static (ScrollRect scroll, RectTransform content) Scroll(string name, Transform parent, RectOffset padding, float spacing, float maxWidth)
        {
            var root = Stretch(Node(name, parent));
            var scroll = root.gameObject.AddComponent<ScrollRect>();

            var viewport = Stretch(Node("Viewport", root));
            var hitArea = viewport.gameObject.AddComponent<Image>();
            hitArea.color = Color.clear;
            viewport.gameObject.AddComponent<RectMask2D>();

            var content = Place(Node("Content", viewport), Vector2.up, Vector2.one, new Vector2(0.5f, 1f), Vector2.zero, Vector2.zero);
            Column(content, padding, spacing);
            Responsive(content, maxWidth, padding.left);
            FitContent(content, horizontal: false, vertical: true);

            scroll.viewport = viewport;
            scroll.content = content;
            scroll.horizontal = false;
            scroll.movementType = ScrollRect.MovementType.Elastic;
            scroll.scrollSensitivity = 24f;
            return (scroll, content);
        }

        public static void Responsive(Component layoutHost, float maxWidth, int minSide)
        {
            var padding = layoutHost.gameObject.AddComponent<ResponsivePadding>();
            SerializedWiring.Set(padding, "maxWidth", maxWidth);
            SerializedWiring.Set(padding, "minSide", minSide);
        }

        public static T Page<T>(string name, Transform parent) where T : AppScreen
        {
            var rect = Stretch(Node(name, parent));
            rect.gameObject.AddComponent<CanvasGroup>();
            return rect.gameObject.AddComponent<T>();
        }

        public static Image Circle(string name, Transform parent, float size, Color colour)
        {
            var rect = Node(name, parent);
            Size(rect, width: size, height: size);
            rect.sizeDelta = Vector2.one * size;
            return Fill(rect, colour, size / 2f);
        }

        public static Image ActivityIndicator(string name, Transform parent, float size, Color colour)
        {
            var rect = Node(name, parent);
            Size(rect, width: size, height: size);
            rect.sizeDelta = Vector2.one * size;
            var image = rect.gameObject.AddComponent<Image>();
            image.sprite = assets.Spinner;
            image.color = colour;
            image.raycastTarget = false;
            rect.gameObject.AddComponent<Spinner>();
            return image;
        }
    }
}

using FloorPlanViz.UI;
using TMPro;
using UnityEngine;
using static FloorPlanViz.Editor.UiKit;
using UButton = UnityEngine.UI.Button;

namespace FloorPlanViz.Editor
{
    static class OverlayBuilder
    {
        const float SheetWidth = 640f;
        const float AlertWidth = 280f;
        const float SheetSlide = -120f;

        static readonly string[] Suggestions =
        {
            "Add a window to the kitchen's outside wall",
            "Make the living room one metre wider",
            "Turn the smallest bedroom into a study",
        };

        public static EditSheet Edit(Transform root)
        {
            var (screen, safe, dismiss) = Overlay<EditSheet>("EditSheet", root, Theme.Scrim);
            var (host, card) = Sheet(safe);
            Heading(card, "Edit with AI", "Describe a change in your own words and the plan is rebuilt.");
            var field = TextField("InstructionField", card, "e.g. add a door between the kitchen and dining room", multiline: true, height: 96f);

            Label("SuggestionsHeader", card, "SUGGESTIONS", TextStyle.Footnote, Theme.SecondaryLabel).margin = new Vector4(4f, 4f, 0f, 0f);
            var chips = new UButton[Suggestions.Length];
            for (var i = 0; i < Suggestions.Length; i++)
                chips[i] = Chip(card, Suggestions[i]);

            var (cancel, apply) = ButtonPair(card, "Cancel", "Apply change");
            Wire(screen, host, new Vector2(0f, SheetSlide));
            SerializedWiring.Set(screen, "instructionField", field);
            SerializedWiring.Set(screen, "applyButton", apply);
            SerializedWiring.Set(screen, "cancelButton", cancel);
            SerializedWiring.Set(screen, "dismissArea", dismiss);
            SerializedWiring.Set(screen, "suggestions", chips);
            return screen;
        }

        public static SettingsSheet Settings(Transform root)
        {
            var (screen, safe, dismiss) = Overlay<SettingsSheet>("SettingsSheet", root, Theme.Scrim);
            var (host, card) = Sheet(safe);
            Heading(card, "Server", "The computer running the Floor Plan backend. It needs to be on the same Wi-Fi as this device.");
            var field = TextField("ServerField", card, "http://192.168.1.10:8000", multiline: false, height: 46f);
            field.keyboardType = TouchScreenKeyboardType.URL;
            var (_, badge) = LibraryBuilder.Connection(card);
            var (test, done) = ButtonPair(card, "Test connection", "Done", ButtonStyle.Tinted);

            Wire(screen, host, new Vector2(0f, SheetSlide));
            SerializedWiring.Set(screen, "serverField", field);
            SerializedWiring.Set(screen, "testButton", test);
            SerializedWiring.Set(screen, "doneButton", done);
            SerializedWiring.Set(screen, "dismissArea", dismiss);
            SerializedWiring.Set(screen, "status", badge);
            return screen;
        }

        public static ActionSheet Actions(Transform root)
        {
            var (screen, safe, dismiss) = Overlay<ActionSheet>("ActionSheet", root, Theme.Scrim);
            var host = BottomHost(safe, 520f, 8);

            var group = Card("Group", host, 14f, Theme.Surface.WithAlpha(0.97f), clip: true);
            Column(group, Pad(0), 0f);
            var title = Label("Title", group, "", TextStyle.Footnote, Theme.SecondaryLabel, TextAlignmentOptions.Center, wrap: false);
            title.margin = new Vector4(16f, 14f, 16f, 14f);

            var template = SheetButton(group, "Action", FontWeight.Regular);
            Fill(Place(Node("Separator", template.transform), Vector2.up, Vector2.one, new Vector2(0.5f, 1f), Vector2.zero, new Vector2(0f, Hairline)), Theme.Separator);

            var cancelCard = Card("CancelCard", host, 14f, clip: true);
            Column(cancelCard, Pad(0), 0f);
            var cancel = SheetButton(cancelCard, "Cancel", FontWeight.SemiBold);

            Wire(screen, host, new Vector2(0f, SheetSlide));
            SerializedWiring.Set(screen, "titleText", title);
            SerializedWiring.Set(screen, "actionGroup", group);
            SerializedWiring.Set(screen, "actionTemplate", template);
            SerializedWiring.Set(screen, "cancelButton", cancel);
            SerializedWiring.Set(screen, "dismissArea", dismiss);
            return screen;
        }

        public static PromptDialog Prompt(Transform root)
        {
            var (screen, safe, _) = Overlay<PromptDialog>("PromptDialog", root, Theme.Scrim);
            var card = Alert(safe);
            var body = Node("Body", card);
            Column(body, Pad(16, 16, 20, 16), 14f);
            var title = Label("Title", body, "Rename", TextStyle.Headline, Theme.Label, TextAlignmentOptions.Center);
            var field = TextField("Field", body, "Name", multiline: false, height: 38f, radius: 8f);

            Separator(card);
            var buttons = Node("Buttons", card);
            Size(buttons, height: 46f);
            Row(buttons, Pad(0), 0f, TextAnchor.MiddleCenter);
            var cancel = TextButton("CancelButton", buttons, "Cancel", ButtonStyle.Plain, height: 46f, radius: 0f);
            Size(cancel, width: 0f, height: 46f, flexibleWidth: 1f);
            var divider = Node("Divider", buttons);
            Size(divider, width: Hairline, height: 46f);
            Fill(divider, Theme.Separator);
            var confirm = TextButton("ConfirmButton", buttons, "Save", ButtonStyle.Plain, height: 46f, radius: 0f);
            Size(confirm, width: 0f, height: 46f, flexibleWidth: 1f);
            var confirmLabel = confirm.GetComponentInChildren<TMP_Text>();
            confirmLabel.fontWeight = FontWeight.SemiBold;

            Wire(screen, card, new Vector2(0f, -16f));
            SerializedWiring.Set(screen, "titleText", title);
            SerializedWiring.Set(screen, "field", field);
            SerializedWiring.Set(screen, "cancelButton", cancel);
            SerializedWiring.Set(screen, "confirmButton", confirm);
            SerializedWiring.Set(screen, "confirmLabel", confirmLabel);
            return screen;
        }

        public static ProcessingOverlay Processing(Transform root)
        {
            var (screen, safe, dismiss) = Overlay<ProcessingOverlay>("Processing", root, Theme.Scrim);
            dismiss.interactable = false;
            var card = Alert(safe);
            var body = Node("Body", card);
            Column(body, Pad(20, 20, 26, 16), 8f, TextAnchor.UpperCenter).childForceExpandWidth = true;
            var spinnerRow = Node("SpinnerRow", body);
            Row(spinnerRow, Pad(0), 0f, TextAnchor.MiddleCenter);
            ActivityIndicator("Spinner", spinnerRow, 34f, Theme.Accent);
            Spacer(body, 4f);
            var title = Label("Title", body, "Working", TextStyle.Headline, Theme.Label, TextAlignmentOptions.Center);
            var stage = Label("Stage", body, "", TextStyle.Subhead, Theme.SecondaryLabel, TextAlignmentOptions.Center);
            var elapsed = Label("Elapsed", body, "", TextStyle.Footnote, Theme.TertiaryLabel, TextAlignmentOptions.Center);
            Separator(card);
            var cancel = TextButton("CancelButton", card, "Cancel", ButtonStyle.Plain, height: 46f, radius: 0f);

            Wire(screen, card, new Vector2(0f, -12f));
            SerializedWiring.Set(screen, "titleText", title);
            SerializedWiring.Set(screen, "stageText", stage);
            SerializedWiring.Set(screen, "elapsedText", elapsed);
            SerializedWiring.Set(screen, "cancelButton", cancel);
            return screen;
        }

        public static Toast ToastBanner(Transform root)
        {
            var screen = Page<Toast>("Toast", root);
            var group = screen.GetComponent<CanvasGroup>();
            group.blocksRaycasts = false;
            group.interactable = false;
            var safe = SafeArea(screen.transform);

            var host = Place(Node("Host", safe), Vector2.up, Vector2.one, new Vector2(0.5f, 1f), Vector2.zero, Vector2.zero);
            Column(host, Pad(16, 16, 10, 0), 0f);
            Responsive(host, 460f, 16);
            FitContent(host, horizontal: false, vertical: true);

            var card = Card("Card", host, 16f);
            DropShadow(card, 14f, 0.18f);
            Row(card, Pad(14, 16, 12, 12), 10f);
            var icon = Icon("Icon", card, Icons.CheckCircle, 22f, Theme.Green);
            var message = Label("Message", card, "", TextStyle.Subhead, Theme.Label);
            Size(message, width: 0f, flexibleWidth: 1f);

            Wire(screen, host, new Vector2(0f, 60f));
            SerializedWiring.Set(screen, "iconText", icon);
            SerializedWiring.Set(screen, "messageText", message);
            return screen;
        }

        static (T screen, RectTransform safe, UButton dismiss) Overlay<T>(string name, Transform root, Color scrim) where T : AppScreen
        {
            var screen = Page<T>(name, root);
            var backdrop = Stretch(Node("Scrim", screen.transform));
            var image = Fill(backdrop, scrim);
            var dismiss = Pressable(backdrop, image, 1f);
            dismiss.transition = UnityEngine.UI.Selectable.Transition.None;
            var safe = SafeArea(screen.transform);
            safe.gameObject.AddComponent<KeyboardAvoider>();
            return (screen, safe, dismiss);
        }

        static RectTransform SafeArea(Transform parent)
        {
            var safe = Stretch(Node("Safe", parent));
            safe.gameObject.AddComponent<SafeAreaPanel>();
            return safe;
        }

        static RectTransform BottomHost(RectTransform safe, float maxWidth, int side)
        {
            var host = Place(Node("Host", safe), Vector2.zero, Vector2.right, new Vector2(0.5f, 0f), Vector2.zero, Vector2.zero);
            Column(host, Pad(side, side, 0, side), 8f);
            Responsive(host, maxWidth, side);
            FitContent(host, horizontal: false, vertical: true);
            return host;
        }

        static (RectTransform host, RectTransform card) Sheet(RectTransform safe)
        {
            var host = BottomHost(safe, SheetWidth, 0);
            var card = Card("Card", host, 16f);
            Column(card, Pad(20, 20, 8, 20), 12f);

            var skirt = Place(Node("Skirt", card), Vector2.zero, Vector2.right, new Vector2(0.5f, 1f), new Vector2(0f, 20f), new Vector2(0f, 400f));
            skirt.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().ignoreLayout = true;
            skirt.SetAsFirstSibling();
            Fill(skirt, Theme.Surface);

            var grabberRow = Node("GrabberRow", card);
            Row(grabberRow, Pad(0, 0, 0, 2), 0f, TextAnchor.MiddleCenter);
            var grabber = Node("Grabber", grabberRow);
            Size(grabber, width: 36f, height: 5f);
            Fill(grabber, Theme.TertiaryLabel, 2.5f);
            return (host, card);
        }

        static RectTransform Alert(RectTransform safe)
        {
            var card = Place(Node("Card", safe), Vector2.one * 0.5f, Vector2.one * 0.5f, Vector2.one * 0.5f, Vector2.zero, new Vector2(AlertWidth, 0f));
            Fill(card, Theme.Surface.WithAlpha(0.98f), 14f);
            card.gameObject.AddComponent<UnityEngine.UI.Mask>();
            Column(card, Pad(0), 0f);
            FitContent(card, horizontal: false, vertical: true);
            return card;
        }

        static void Heading(Transform card, string title, string detail)
        {
            var block = Node("Heading", card);
            Column(block, Pad(4, 4, 6, 2), 4f);
            Label("Title", block, title, TextStyle.Title3, Theme.Label);
            Label("Detail", block, detail, TextStyle.Subhead, Theme.SecondaryLabel);
        }

        static UButton Chip(Transform parent, string text)
        {
            var button = TextButton("Suggestion", parent, text, ButtonStyle.Tinted, height: 40f, radius: 10f);
            var label = button.GetComponentInChildren<TMP_Text>();
            label.fontWeight = FontWeight.Regular;
            label.fontSize = 15f;
            label.alignment = TextAlignmentOptions.Left;
            var content = button.transform.Find("Content").GetComponent<UnityEngine.UI.HorizontalLayoutGroup>();
            content.childAlignment = TextAnchor.MiddleLeft;
            content.padding = Pad(14, 14, 0, 0);
            return button;
        }

        static (UButton secondary, UButton primary) ButtonPair(Transform parent, string secondary, string primary, ButtonStyle secondaryStyle = ButtonStyle.Gray)
        {
            var row = Node("Buttons", parent);
            Row(row, Pad(0, 0, 6, 0), 10f, TextAnchor.MiddleCenter, expand: true);
            return (TextButton("SecondaryButton", row, secondary, secondaryStyle), TextButton("PrimaryButton", row, primary, ButtonStyle.Filled));
        }

        static UButton SheetButton(Transform parent, string label, FontWeight weight)
        {
            var button = TextButton(label + "Button", parent, label, ButtonStyle.Plain, height: 56f, radius: 0f);
            var text = button.GetComponentInChildren<TMP_Text>();
            text.fontSize = 20f;
            text.fontWeight = weight;
            text.characterSpacing = -0.8f;
            return button;
        }

        static void Wire(AppScreen screen, RectTransform panel, Vector2 slideFrom)
        {
            SerializedWiring.Set(screen, "slidingPanel", panel);
            SerializedWiring.Set(screen, "slideFrom", slideFrom);
        }
    }
}

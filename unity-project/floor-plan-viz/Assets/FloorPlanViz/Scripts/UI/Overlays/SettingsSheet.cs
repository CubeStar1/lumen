using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    public enum ConnectionState
    {
        Checking,
        Online,
        Offline,
    }

    /// <summary>Bottom sheet for the server address, with a connection check.</summary>
    public sealed class SettingsSheet : AppScreen
    {
        [SerializeField] TMP_InputField serverField;
        [SerializeField] Button testButton;
        [SerializeField] Button doneButton;
        [SerializeField] Button dismissArea;
        [SerializeField] ConnectionBadge status;

        public event Action<string> TestRequested;
        public event Action<string> Closed;

        string Url => serverField.text.Trim();

        void Awake()
        {
            serverField.shouldHideMobileInput = true;
            testButton.onClick.AddListener(() => TestRequested?.Invoke(Url));
            doneButton.onClick.AddListener(() => Closed?.Invoke(Url));
            dismissArea.onClick.AddListener(() => Closed?.Invoke(Url));
        }

        public void Show(string url, ConnectionState state, string detail)
        {
            serverField.SetTextWithoutNotify(url);
            SetStatus(state, detail);
            SetVisible(true);
        }

        public void SetStatus(ConnectionState state, string detail) => status.Set(state, detail);
    }
}

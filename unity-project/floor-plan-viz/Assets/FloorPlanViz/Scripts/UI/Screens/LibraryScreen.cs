using System;
using System.Collections.Generic;
using FloorPlanViz.Data;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Home page: start a new plan, try the sample, or reopen a saved plan.</summary>
    public sealed class LibraryScreen : AppScreen
    {
        [SerializeField] Button settingsButton;
        [SerializeField] Button connectionButton;
        [SerializeField] ConnectionBadge connection;
        [SerializeField] Button newPlanButton;
        [SerializeField] Button sampleButton;
        [SerializeField] Button refreshButton;
        [SerializeField] RectTransform listGroup;
        [SerializeField] PlanRow rowTemplate;
        [SerializeField] GameObject listCard;
        [SerializeField] GameObject messageCard;
        [SerializeField] TMP_Text messageTitle;
        [SerializeField] TMP_Text messageDetail;
        [SerializeField] GameObject loadingIndicator;
        [SerializeField] ScrollRect scroll;

        public event Action NewPlanRequested;
        public event Action SampleRequested;
        public event Action SettingsRequested;
        public event Action RefreshRequested;
        public event Action<PlanSummary> PlanSelected;

        void Awake()
        {
            settingsButton.onClick.AddListener(() => SettingsRequested?.Invoke());
            connectionButton.onClick.AddListener(() => SettingsRequested?.Invoke());
            newPlanButton.onClick.AddListener(() => NewPlanRequested?.Invoke());
            sampleButton.onClick.AddListener(() => SampleRequested?.Invoke());
            refreshButton.onClick.AddListener(() => RefreshRequested?.Invoke());
            rowTemplate.gameObject.SetActive(false);
        }

        public void SetConnection(ConnectionState state, string detail) => connection.Set(state, detail);

        public void ShowLoading()
        {
            loadingIndicator.SetActive(true);
            refreshButton.gameObject.SetActive(false);
        }

        public void ShowPlans(IReadOnlyList<PlanSummary> plans, Func<string, Awaitable<Texture2D>> thumbnails)
        {
            StopLoading();
            ClearRows();
            if (plans.Count == 0)
            {
                ShowMessage("No plans yet", "Plans you scan are saved here so you can open them again later.");
                return;
            }

            messageCard.SetActive(false);
            listCard.SetActive(true);
            for (var i = 0; i < plans.Count; i++)
            {
                var plan = plans[i];
                var row = Instantiate(rowTemplate, listGroup);
                row.gameObject.SetActive(true);
                row.Bind(plan, i == plans.Count - 1, () => PlanSelected?.Invoke(plan), () => thumbnails(plan.Id));
            }
        }

        public void ShowUnavailable(string detail)
        {
            StopLoading();
            ClearRows();
            ShowMessage("Can't load your plans", detail);
        }

        public void ScrollToTop() => scroll.verticalNormalizedPosition = 1f;

        void ShowMessage(string title, string detail)
        {
            listCard.SetActive(false);
            messageCard.SetActive(true);
            messageTitle.text = title;
            messageDetail.text = detail;
        }

        void StopLoading()
        {
            loadingIndicator.SetActive(false);
            refreshButton.gameObject.SetActive(true);
        }

        void ClearRows()
        {
            foreach (Transform child in listGroup)
            {
                if (child != rowTemplate.transform)
                    Destroy(child.gameObject);
            }
        }
    }
}

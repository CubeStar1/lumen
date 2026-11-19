using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using FloorPlanViz.Api;
using FloorPlanViz.Data;
using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>The app's navigation: Library → Plan detail → AR, with the sheets and dialogs on top.</summary>
    public sealed class AppFlow : MonoBehaviour
    {
        const int MaxImageSize = 2048;
        const int MaxSheetSize = 4096;
        const int JpegQuality = 90;
        const float PollSeconds = 1.5f;

        static readonly string[] EditStages = { "Sending your change", "Updating the plan", "Rebuilding the model" };

        [SerializeField] ApiSettings apiSettings;
        [SerializeField] TextAsset samplePlan;
        [SerializeField] GameObject backdrop;
        [SerializeField] RequestRunner requests;
        [SerializeField] ArExperience ar;

        [SerializeField] LibraryScreen library;
        [SerializeField] PlanDetailScreen detail;
        [SerializeField] ArHud hud;
        [SerializeField] EditSheet editSheet;
        [SerializeField] SettingsSheet settingsSheet;
        [SerializeField] ActionSheet actionSheet;
        [SerializeField] PromptDialog promptDialog;
        [SerializeField] Toast toast;

        PlanApiClient api;
        ThumbnailCache thumbnails;
        PlanDocument current;
        CancellationTokenSource libraryLoad;
        (ConnectionState state, string detail) connection = (ConnectionState.Checking, "Connecting…");

        AppScreen[] Pages => new AppScreen[] { library, detail, hud };

        void Awake()
        {
            api = new PlanApiClient(apiSettings);
            thumbnails = new ThumbnailCache(api);

            library.NewPlanRequested += ChooseNewPlan;
            library.SampleRequested += () => OpenDetail(PlanDocument.Sample(PlanJson.Deserialize<PlanResponse>(samplePlan.text)));
            library.SettingsRequested += () => settingsSheet.Show(apiSettings.BaseUrl, connection.state, connection.detail);
            library.RefreshRequested += RefreshLibrary;
            library.PlanSelected += OpenSaved;

            detail.BackRequested += ShowLibrary;
            detail.MoreRequested += ShowPlanActions;
            detail.ViewRequested += EnterAr;

            ar.CloseRequested += ExitAr;
            ar.EditRequested += editSheet.Show;
            editSheet.Submitted += ApplyEdit;
            editSheet.Cancelled += () => editSheet.SetVisible(false);

            settingsSheet.TestRequested += TestServer;
            settingsSheet.Closed += CloseSettings;
        }

        void Start()
        {
            foreach (var overlay in new AppScreen[] { editSheet, settingsSheet, actionSheet, promptDialog, toast })
                overlay.SetVisible(false);
            ar.Exit();
            ShowLibrary();
        }

        void OnDestroy()
        {
            libraryLoad?.Cancel();
            thumbnails.Clear();
        }

        void ShowPage(AppScreen page)
        {
            foreach (var candidate in Pages)
                candidate.SetVisible(candidate == page);
            backdrop.SetActive(page != hud);
        }

        void ShowLibrary()
        {
            current = null;
            ShowPage(library);
            library.ScrollToTop();
            RefreshLibrary();
        }

        async void RefreshLibrary()
        {
            libraryLoad?.Cancel();
            libraryLoad = new CancellationTokenSource();
            var token = libraryLoad.Token;
            library.ShowLoading();
            SetConnection(ConnectionState.Checking, "Connecting…");
            try
            {
                var health = await api.HealthAsync(token);
                SetConnection(ConnectionState.Online, $"Connected · {health.Model}");
                var plans = await api.ListAsync(token);
                library.ShowPlans(plans, id => thumbnails.GetAsync(id, token));
            }
            catch (System.OperationCanceledException)
            {
            }
            catch (PlanApiException error)
            {
                SetConnection(ConnectionState.Offline, "Server offline · Tap to change");
                library.ShowUnavailable(error.Message);
            }
        }

        void SetConnection(ConnectionState state, string text)
        {
            connection = (state, text);
            library.SetConnection(state, text);
            settingsSheet.SetStatus(state, text);
        }

        void ChooseNewPlan() =>
            actionSheet.Show("New plan",
                new SheetAction("Single floor plan", () => PickAndParse(ParseKind.Floor)),
                new SheetAction("Whole building · one sheet", () => PickAndParse(ParseKind.Sheet)),
                new SheetAction("Whole building · photo per floor", () => PickAndParse(ParseKind.Photos)));

        async void PickAndParse(ParseKind kind)
        {
            var images = await PickImages(kind);
            if (images.Count == 0)
                return;

            var jpegs = images.Select(image => image.EncodeToJPG(JpegQuality)).ToList();
            foreach (var image in images)
                Destroy(image);
            var title = kind == ParseKind.Floor ? "Reading your floor plan" : "Reading your building";
            await requests.Run(title, (token, report) => ParseAsync(kind, jpegs, report, token), saved =>
            {
                OpenDetail(PlanDocument.From(saved));
                toast.Show("Saved to your plans", ToastKind.Success);
            });
        }

        static async Awaitable<List<Texture2D>> PickImages(ParseKind kind)
        {
            if (kind == ParseKind.Photos)
                return await ImagePicker.PickManyAsync(MaxImageSize, "Choose a photo of each floor");
            var image = await ImagePicker.PickAsync(kind == ParseKind.Sheet ? MaxSheetSize : MaxImageSize);
            return image == null ? new List<Texture2D>() : new List<Texture2D> { image };
        }

        async Awaitable<SavedPlan> ParseAsync(ParseKind kind, List<byte[]> jpegs, Action<string> report, CancellationToken token)
        {
            report(jpegs.Count > 1 ? $"Uploading {jpegs.Count} photos" : "Uploading your image");
            var job = await api.StartJobAsync(kind, jpegs, token);
            while (job.State == JobState.Running)
            {
                report(Describe(job));
                await Awaitable.WaitForSecondsAsync(PollSeconds, token);
                job = await api.JobAsync(job.Id, token);
            }
            if (job.State == JobState.Failed)
                throw new PlanApiException(job.Error ?? "The plan could not be read.");
            report("Opening the plan");
            return await api.GetAsync(job.PlanId, token);
        }

        static string Describe(ParseJob job) =>
            job.Stages.Count <= 1 ? job.Stage : $"{job.Stage} · {job.StagesDone} of {job.Stages.Count} done";

        async void OpenSaved(PlanSummary summary)
        {
            await requests.Run("Opening plan", null, token => api.GetAsync(summary.Id, token),
                saved => OpenDetail(PlanDocument.From(saved)));
        }

        void OpenDetail(PlanDocument document)
        {
            current = document;
            ShowPage(detail);
            detail.Show(document);
        }

        void ShowPlanActions()
        {
            actionSheet.Show(current.Name,
                new SheetAction("Rename", () => promptDialog.Show("Rename plan", current.Name, "Save", RenamePlan)),
                new SheetAction("Delete plan", DeletePlan, destructive: true));
        }

        async void RenamePlan(string name)
        {
            var document = current;
            await requests.Run("Renaming", null, token => api.RenameAsync(document.Id, name, token), saved =>
            {
                document.Name = saved.Name;
                detail.SetName(saved.Name);
            });
        }

        async void DeletePlan()
        {
            var id = current.Id;
            await requests.Run("Deleting", null, async token =>
            {
                await api.DeleteAsync(id, token);
                return true;
            }, _ =>
            {
                thumbnails.Forget(id);
                ShowLibrary();
                toast.Show("Plan deleted", ToastKind.Success);
            });
        }

        void EnterAr()
        {
            ShowPage(hud);
            ar.Enter(current);
        }

        void ExitAr()
        {
            editSheet.SetVisible(false);
            ar.Exit();
            OpenDetail(current);
        }

        async void ApplyEdit(string instruction)
        {
            editSheet.SetVisible(false);
            var document = current;
            var level = ar.IsActive ? ar.SelectedLevel : document.Plan.Geometry.Ground.Index;
            if (document.IsSaved)
            {
                await requests.Run("Applying your change", EditStages, token => api.EditAsync(document.Id, instruction, level, token),
                    saved => ShowEdited(document, saved.Plan));
            }
            else
            {
                await requests.Run("Applying your change", EditStages, token => api.EditUnsavedAsync(document.Plan, instruction, level, token),
                    plan => ShowEdited(document, plan));
            }
        }

        void ShowEdited(PlanDocument document, PlanResponse plan)
        {
            document.Plan = plan;
            if (ar.IsActive)
                ar.Rebuild(plan);
            var message = plan.Warnings.Count > 0 ? $"Updated, with a note: {plan.Warnings[0]}" : "Plan updated";
            toast.Show(message, ToastKind.Success);
        }

        async void TestServer(string url)
        {
            apiSettings.BaseUrl = url;
            settingsSheet.SetStatus(ConnectionState.Checking, "Checking…");
            try
            {
                var health = await api.HealthAsync(destroyCancellationToken);
                settingsSheet.SetStatus(ConnectionState.Online, $"Connected · {health.Model}");
            }
            catch (PlanApiException error)
            {
                settingsSheet.SetStatus(ConnectionState.Offline, error.Message);
            }
        }

        void CloseSettings(string url)
        {
            settingsSheet.SetVisible(false);
            apiSettings.BaseUrl = url;
            thumbnails.Clear();
            RefreshLibrary();
        }
    }
}

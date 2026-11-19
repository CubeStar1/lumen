using System;
using System.Threading;
using FloorPlanViz.Api;
using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>Runs a server call behind the progress overlay; errors become toasts unless the caller handles them.</summary>
    public sealed class RequestRunner : MonoBehaviour
    {
        [SerializeField] ProcessingOverlay overlay;
        [SerializeField] Toast toast;

        CancellationTokenSource pending;

        public bool IsBusy => pending != null;

        void Awake() => overlay.Cancelled += () => pending?.Cancel();

        void OnDestroy() => pending?.Cancel();

        /// <summary>Runs a call that reports its own progress through the overlay.</summary>
        public Awaitable Run<T>(string title, Func<CancellationToken, Action<string>, Awaitable<T>> call, Action<T> onSuccess) =>
            Run(title, null, token => call(token, overlay.Report), onSuccess);

        public async Awaitable Run<T>(string title, string[] stages, Func<CancellationToken, Awaitable<T>> call,
            Action<T> onSuccess, Action<string> onError = null)
        {
            if (IsBusy)
                return;
            pending = new CancellationTokenSource();
            overlay.Show(title, stages);
            try
            {
                var result = await call(pending.Token);
                overlay.SetVisible(false);
                onSuccess(result);
            }
            catch (OperationCanceledException)
            {
                overlay.SetVisible(false);
            }
            catch (Exception error)
            {
                overlay.SetVisible(false);
                if (error is not PlanApiException)
                    Debug.LogException(error);
                var message = error is PlanApiException ? error.Message : "Something went wrong while reading the response.";
                if (onError != null)
                    onError(message);
                else
                    toast.Show(message, ToastKind.Error);
            }
            finally
            {
                pending.Dispose();
                pending = null;
            }
        }
    }
}

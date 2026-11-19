using System;
using System.Collections.Generic;
using System.Threading;
using FloorPlanViz.Data;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Networking;

namespace FloorPlanViz.Api
{
    public sealed class PlanApiClient
    {
        const int QuickTimeoutSeconds = 6;

        sealed class EditRequest
        {
            public object Spec { get; set; }
            public string Instruction { get; set; }
            public int Level { get; set; }
        }

        sealed class InstructionRequest
        {
            public string Instruction { get; set; }
            public int Level { get; set; }
        }

        sealed class RenameRequest
        {
            public string Name { get; set; }
        }

        public sealed class Health
        {
            public string Status { get; set; }
            public string Model { get; set; }
        }

        readonly ApiSettings settings;

        public PlanApiClient(ApiSettings settings)
        {
            this.settings = settings;
        }

        string Url(string path) => $"{settings.BaseUrl}{path}";

        public Awaitable<Health> HealthAsync(CancellationToken cancellation) =>
            SendAsync<Health>(UnityWebRequest.Get(Url("/health")), cancellation, QuickTimeoutSeconds);

        public Awaitable<List<PlanSummary>> ListAsync(CancellationToken cancellation) =>
            SendAsync<List<PlanSummary>>(UnityWebRequest.Get(Url("/plans")), cancellation, QuickTimeoutSeconds);

        public Awaitable<SavedPlan> GetAsync(string id, CancellationToken cancellation) =>
            SendAsync<SavedPlan>(UnityWebRequest.Get(Url($"/plans/{id}")), cancellation);

        public Awaitable<SavedPlan> ParseAsync(byte[] jpeg, CancellationToken cancellation)
        {
            var form = new List<IMultipartFormSection>
            {
                new MultipartFormFileSection("image", jpeg, "plan.jpg", "image/jpeg"),
            };
            return SendAsync<SavedPlan>(UnityWebRequest.Post(Url("/plans/parse"), form), cancellation);
        }

        public Awaitable<SavedPlan> EditAsync(string id, string instruction, int level, CancellationToken cancellation) =>
            SendAsync<SavedPlan>(Json("POST", $"/plans/{id}/edit", new InstructionRequest { Instruction = instruction, Level = level }), cancellation);

        public Awaitable<PlanResponse> EditUnsavedAsync(PlanResponse plan, string instruction, int level, CancellationToken cancellation) =>
            SendAsync<PlanResponse>(Json("POST", "/plans/edit", new EditRequest { Spec = plan.Spec, Instruction = instruction, Level = level }),
                cancellation);

        public Awaitable<SavedPlan> RenameAsync(string id, string name, CancellationToken cancellation) =>
            SendAsync<SavedPlan>(Json("PATCH", $"/plans/{id}", new RenameRequest { Name = name }), cancellation, QuickTimeoutSeconds);

        public async Awaitable DeleteAsync(string id, CancellationToken cancellation)
        {
            using var request = UnityWebRequest.Delete(Url($"/plans/{id}"));
            await SendRawAsync(request, cancellation, QuickTimeoutSeconds);
        }

        public async Awaitable<Texture2D> ThumbnailAsync(string id, CancellationToken cancellation)
        {
            using var request = UnityWebRequestTexture.GetTexture(Url($"/plans/{id}/thumbnail"));
            await SendRawAsync(request, cancellation, QuickTimeoutSeconds);
            return DownloadHandlerTexture.GetContent(request);
        }

        UnityWebRequest Json(string method, string path, object body)
        {
            var request = new UnityWebRequest(Url(path), method)
            {
                uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(PlanJson.Serialize(body))),
                downloadHandler = new DownloadHandlerBuffer(),
            };
            request.SetRequestHeader("Content-Type", "application/json");
            return request;
        }

        async Awaitable<T> SendAsync<T>(UnityWebRequest request, CancellationToken cancellation, int timeout = 0)
        {
            using (request)
            {
                await SendRawAsync(request, cancellation, timeout);
                return PlanJson.Deserialize<T>(request.downloadHandler.text);
            }
        }

        async Awaitable SendRawAsync(UnityWebRequest request, CancellationToken cancellation, int timeout)
        {
            request.timeout = timeout > 0 ? timeout : settings.TimeoutSeconds;
            using (cancellation.Register(request.Abort))
                await request.SendWebRequest();

            cancellation.ThrowIfCancellationRequested();
            if (request.result != UnityWebRequest.Result.Success)
                throw new PlanApiException(DescribeFailure(request));
        }

        static string DescribeFailure(UnityWebRequest request)
        {
            if (request.result == UnityWebRequest.Result.ConnectionError)
                return $"Couldn't reach the server at {request.uri.GetLeftPart(UriPartial.Authority)}. " +
                       "Check that it's running and on the same Wi-Fi.";

            return ServerDetail(request.downloadHandler?.text) ?? $"Server error ({request.responseCode}).";
        }

        static string ServerDetail(string body)
        {
            if (string.IsNullOrEmpty(body))
                return null;
            try
            {
                return JObject.Parse(body)["detail"] is JValue { Type: JTokenType.String } detail
                    ? detail.ToString()
                    : null;
            }
            catch (JsonException)
            {
                return null;
            }
        }
    }
}

using System.Collections.Generic;
using System.Threading;
using FloorPlanViz.Api;
using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>Downloads plan thumbnails once and keeps them for the session.</summary>
    public sealed class ThumbnailCache
    {
        readonly PlanApiClient api;
        readonly Dictionary<string, Texture2D> textures = new();

        public ThumbnailCache(PlanApiClient api)
        {
            this.api = api;
        }

        public async Awaitable<Texture2D> GetAsync(string id, CancellationToken cancellation)
        {
            if (textures.TryGetValue(id, out var cached))
                return cached;
            try
            {
                var texture = await api.ThumbnailAsync(id, cancellation);
                textures[id] = texture;
                return texture;
            }
            catch (PlanApiException)
            {
                return null;
            }
        }

        public void Forget(string id)
        {
            if (textures.Remove(id, out var texture))
                Object.Destroy(texture);
        }

        public void Clear()
        {
            foreach (var texture in textures.Values)
                Object.Destroy(texture);
            textures.Clear();
        }
    }
}

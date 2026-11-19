using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using Newtonsoft.Json.Linq;
using Newtonsoft.Json.Serialization;

namespace FloorPlanViz.Api
{
    /// <summary>JSON settings matching the backend's snake_case wire format.</summary>
    public static class PlanJson
    {
        static readonly JsonSerializerSettings Settings = new()
        {
            ContractResolver = new DefaultContractResolver { NamingStrategy = new SnakeCaseNamingStrategy() },
            Converters = { new StringEnumConverter(new SnakeCaseNamingStrategy()) },
        };

        public static T Deserialize<T>(string json) => JsonConvert.DeserializeObject<T>(json, Settings);

        public static string Serialize(object value) => JsonConvert.SerializeObject(value, Settings);

        /// <summary>The model's notes for each level of the plan's spec, prefixed with the level name when there are several.</summary>
        public static IEnumerable<string> Notes(PlanResponse plan)
        {
            if (plan.Spec is not JObject spec || spec["levels"] is not JArray levels)
                return Enumerable.Empty<string>();
            var floors = levels.Select(level => level["floor"]).Where(floor => floor != null).ToList();
            return floors
                .Select(floor => (name: (string)floor["name"], notes: (string)floor["notes"]))
                .Where(f => !string.IsNullOrWhiteSpace(f.notes))
                .Select(f => floors.Count > 1 ? $"<b>{f.name}:</b> {f.notes}" : f.notes);
        }
    }
}

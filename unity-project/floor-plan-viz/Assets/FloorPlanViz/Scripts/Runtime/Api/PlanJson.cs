using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
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
    }
}

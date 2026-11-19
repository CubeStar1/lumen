using UnityEngine;

namespace FloorPlanViz.Api
{
    [CreateAssetMenu(menuName = "Floor Plan Viz/API Settings")]
    public sealed class ApiSettings : ScriptableObject
    {
        const string BaseUrlKey = "FloorPlanViz.BaseUrl";

        [SerializeField] string defaultBaseUrl = "http://192.168.1.10:8000";
        [SerializeField] int timeoutSeconds = 180;

        public int TimeoutSeconds => timeoutSeconds;

        /// <summary>The backend URL, remembered on the device once the user changes it.</summary>
        public string BaseUrl
        {
            get => PlayerPrefs.GetString(BaseUrlKey, defaultBaseUrl);
            set
            {
                PlayerPrefs.SetString(BaseUrlKey, value.Trim().TrimEnd('/'));
                PlayerPrefs.Save();
            }
        }
    }
}

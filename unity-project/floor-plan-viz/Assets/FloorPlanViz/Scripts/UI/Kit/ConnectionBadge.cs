using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>A coloured dot and a line of text describing whether the server can be reached.</summary>
    public sealed class ConnectionBadge : MonoBehaviour
    {
        [SerializeField] Image dot;
        [SerializeField] TMP_Text label;

        public void Set(ConnectionState state, string detail)
        {
            dot.color = state switch
            {
                ConnectionState.Online => Theme.Green,
                ConnectionState.Offline => Theme.Red,
                _ => Theme.TertiaryLabel,
            };
            label.text = detail;
        }
    }
}

using FloorPlanViz.Data;
using FloorPlanViz.Model;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    public sealed class RoomRow : MonoBehaviour
    {
        [SerializeField] Image iconBackground;
        [SerializeField] TMP_Text iconText;
        [SerializeField] TMP_Text nameText;
        [SerializeField] TMP_Text typeText;
        [SerializeField] TMP_Text areaText;
        [SerializeField] GameObject separator;

        public void Bind(RoomData room, bool last)
        {
            iconBackground.color = RoomStyle.Colour(room.Type);
            iconText.text = RoomStyle.Icon(room.Type);
            nameText.text = RoomLabel.TitleCase(room.Name);
            typeText.text = RoomStyle.Name(room.Type);
            areaText.text = Format.Area(room.Area);
            separator.SetActive(!last);
        }
    }
}

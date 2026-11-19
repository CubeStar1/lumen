using UnityEngine;

namespace FloorPlanViz.UI
{
    public sealed class Spinner : MonoBehaviour
    {
        [SerializeField] float degreesPerSecond = 300f;

        void Update() => transform.Rotate(0f, 0f, -degreesPerSecond * Time.unscaledDeltaTime);
    }
}

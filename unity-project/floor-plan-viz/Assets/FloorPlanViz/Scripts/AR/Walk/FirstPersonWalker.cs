using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;

namespace FloorPlanViz.AR
{
    /// <summary>A game-style first-person body: the left thumbstick walks, dragging the right of the screen looks around,
    /// and a character controller keeps it on the floors and stairs and out of the walls. WASD and the arrow keys work in the Editor.</summary>
    [RequireComponent(typeof(CharacterController))]
    public sealed class FirstPersonWalker : MonoBehaviour
    {
        const float BodyHeight = 1.75f;
        const float BodyRadius = 0.22f;
        const float StepHeight = 0.32f;
        const float EyeHeight = 1.6f;
        const float WalkSpeed = 1.9f;
        const float Acceleration = 9f;
        const float Gravity = 18f;
        const float GroundStick = 2f;
        const float LookDegreesPerScreen = 180f;
        const float KeyTurnDegreesPerSecond = 120f;
        const float MaxPitch = 80f;
        const float FallLimit = 8f;
        const float SpawnLift = 0.05f;
        const float BobHeight = 0.03f;
        const float BobStridesPerMetre = 1.6f;

        [SerializeField] Camera view;
        [SerializeField] Camera arView;
        [SerializeField] VirtualJoystick joystick;
        [SerializeField] LookPad lookPad;

        CharacterController body;
        Vector3 spawn;
        float spawnHeading;
        float yaw;
        float pitch;
        Vector3 planarVelocity;
        float verticalSpeed;
        float bobPhase;
        float bob;

        public bool IsActive => gameObject.activeSelf;

        void Awake()
        {
            body = GetComponent<CharacterController>();
            body.height = BodyHeight;
            body.radius = BodyRadius;
            body.center = Vector3.up * (BodyHeight / 2f);
            body.stepOffset = StepHeight;
            body.slopeLimit = 50f;
            body.skinWidth = 0.02f;
            body.minMoveDistance = 0f;
        }

        /// <summary>Takes over the view and stands the body at <paramref name="feet"/>, facing <paramref name="heading"/> degrees.</summary>
        public void Begin(Vector3 feet, float heading)
        {
            spawn = feet;
            spawnHeading = heading;
            gameObject.SetActive(true);
            arView.enabled = false;
            Respawn();
        }

        public void End()
        {
            if (!IsActive)
                return;
            gameObject.SetActive(false);
            arView.enabled = true;
        }

        void Update()
        {
            var dt = Time.deltaTime;
            Look(lookPad.TakeDelta() / Mathf.Min(Screen.width, Screen.height) * LookDegreesPerScreen + KeyboardTurn() * dt);
            Move(Vector2.ClampMagnitude(joystick.Value + KeyboardMove(), 1f), dt);
            if (transform.position.y < spawn.y - FallLimit)
                Respawn();
            view.transform.localPosition = Vector3.up * (EyeHeight + bob);
            view.transform.localRotation = Quaternion.Euler(pitch, 0f, 0f);
        }

        void Look(Vector2 degrees)
        {
            yaw += degrees.x;
            pitch = Mathf.Clamp(pitch - degrees.y, -MaxPitch, MaxPitch);
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        }

        void Move(Vector2 input, float dt)
        {
            var target = transform.rotation * new Vector3(input.x, 0f, input.y) * WalkSpeed;
            planarVelocity = Vector3.MoveTowards(planarVelocity, target, Acceleration * dt);
            verticalSpeed = body.isGrounded ? -GroundStick : verticalSpeed - Gravity * dt;
            body.Move((planarVelocity + Vector3.up * verticalSpeed) * dt);

            var speed = body.isGrounded ? new Vector3(body.velocity.x, 0f, body.velocity.z).magnitude : 0f;
            bobPhase += speed * BobStridesPerMetre * Mathf.PI * dt;
            bob = Mathf.Lerp(bob, Mathf.Sin(bobPhase) * BobHeight * Mathf.Clamp01(speed / WalkSpeed), 12f * dt);
        }

        void Respawn()
        {
            body.enabled = false;
            transform.position = spawn + Vector3.up * SpawnLift;
            body.enabled = true;
            yaw = spawnHeading;
            pitch = 0f;
            planarVelocity = Vector3.zero;
            verticalSpeed = 0f;
            bob = 0f;
            Look(Vector2.zero);
        }

        static Vector2 KeyboardMove()
        {
            var keys = Keyboard.current;
            if (keys == null)
                return Vector2.zero;
            return new Vector2(Axis(keys.dKey, keys.aKey), Axis(keys.wKey, keys.sKey) + Axis(keys.upArrowKey, keys.downArrowKey));
        }

        static Vector2 KeyboardTurn()
        {
            var keys = Keyboard.current;
            return keys == null ? Vector2.zero : new Vector2(Axis(keys.rightArrowKey, keys.leftArrowKey) * KeyTurnDegreesPerSecond, 0f);
        }

        static float Axis(KeyControl positive, KeyControl negative) =>
            (positive.isPressed ? 1f : 0f) - (negative.isPressed ? 1f : 0f);
    }
}

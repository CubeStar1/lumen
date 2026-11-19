using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace FloorPlanViz.Editor
{
    /// <summary>Assigns private [SerializeField] values from editor tooling.</summary>
    static class SerializedWiring
    {
        public static void Set(Object target, string field, Object value) =>
            Apply(target, field, p => p.objectReferenceValue = value);

        public static void Set(Object target, string field, float value) =>
            Apply(target, field, p => p.floatValue = value);

        public static void Set(Object target, string field, int value) =>
            Apply(target, field, p => p.intValue = value);

        public static void Set(Object target, string field, bool value) =>
            Apply(target, field, p => p.boolValue = value);

        public static void Set(Object target, string field, Vector2 value) =>
            Apply(target, field, p => p.vector2Value = value);

        public static void Set<T>(Object target, string field, IReadOnlyList<T> values) where T : Object =>
            Apply(target, field, p =>
            {
                p.arraySize = values.Count;
                for (var i = 0; i < values.Count; i++)
                    p.GetArrayElementAtIndex(i).objectReferenceValue = values[i];
            });

        static void Apply(Object target, string field, System.Action<SerializedProperty> assign)
        {
            var serialized = new SerializedObject(target);
            var property = serialized.FindProperty(field)
                ?? throw new System.ArgumentException($"{target.GetType().Name} has no serialized field '{field}'.");
            assign(property);
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}

using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace FloorPlanViz.Geometry
{
    /// <summary>Accumulates faces and turns them into a single mesh. UVs are in metres.</summary>
    public sealed class MeshData
    {
        readonly List<Vector3> vertices = new();
        readonly List<Vector3> normals = new();
        readonly List<Vector2> uvs = new();
        readonly List<int> triangles = new();

        public bool IsEmpty => vertices.Count == 0;
        public int TriangleCount => triangles.Count / 3;

        public void AddBox(Vector3 center, Quaternion rotation, Vector3 size, bool includeTop = true)
        {
            var x = rotation * Vector3.right;
            var y = rotation * Vector3.up;
            var z = rotation * Vector3.forward;
            var half = size / 2f;

            AddFace(center + x * half.x, x, y, size.z, size.y);
            AddFace(center - x * half.x, -x, y, size.z, size.y);
            if (includeTop)
                AddFace(center + y * half.y, y, z, size.x, size.z);
            AddFace(center - y * half.y, -y, z, size.x, size.z);
            AddFace(center + z * half.z, z, y, size.x, size.y);
            AddFace(center - z * half.z, -z, y, size.x, size.y);
        }

        /// <summary>Adds a rectangle centred on <paramref name="center"/>, visible from the side its normal points to.</summary>
        public void AddFace(Vector3 center, Vector3 normal, Vector3 up, float width, float height)
        {
            var right = Vector3.Cross(normal, up) * (width / 2f);
            var top = up * (height / 2f);
            var start = vertices.Count;

            AddVertex(center - right + top, normal, new Vector2(0f, height));
            AddVertex(center + right + top, normal, new Vector2(width, height));
            AddVertex(center + right - top, normal, new Vector2(width, 0f));
            AddVertex(center - right - top, normal, new Vector2(0f, 0f));
            triangles.AddRange(new[] { start, start + 1, start + 2, start, start + 2, start + 3 });
        }

        /// <summary>Adds a horizontal polygon given in plan coordinates (plan y maps to world z).</summary>
        public void AddPolygon(IReadOnlyList<Vector2> polygon, float height, bool faceUp)
        {
            var normal = faceUp ? Vector3.up : Vector3.down;
            var start = vertices.Count;
            foreach (var p in polygon)
                AddVertex(new Vector3(p.x, height, p.y), normal, p);

            var indices = PolygonTriangulator.Triangulate(polygon);
            for (var i = 0; i < indices.Count; i += 3)
            {
                if (faceUp)
                    triangles.AddRange(new[] { start + indices[i], start + indices[i + 2], start + indices[i + 1] });
                else
                    triangles.AddRange(new[] { start + indices[i], start + indices[i + 1], start + indices[i + 2] });
            }
        }

        public Mesh ToMesh(string name)
        {
            var mesh = new Mesh { name = name };
            if (vertices.Count > ushort.MaxValue)
                mesh.indexFormat = IndexFormat.UInt32;
            mesh.SetVertices(vertices);
            mesh.SetNormals(normals);
            mesh.SetUVs(0, uvs);
            mesh.SetTriangles(triangles, 0);
            mesh.RecalculateBounds();
            mesh.RecalculateTangents();
            return mesh;
        }

        void AddVertex(Vector3 position, Vector3 normal, Vector2 uv)
        {
            vertices.Add(position);
            normals.Add(normal);
            uvs.Add(uv);
        }
    }
}

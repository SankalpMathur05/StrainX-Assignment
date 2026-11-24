/** Titled bullet list; renders nothing when empty. */
export function TextList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="micro mb-1">{title}</p>
      <ul className="list-disc space-y-1 pl-5 text-sm">
        {items.map((item, i) => (
          <li key={`${i}-${item}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

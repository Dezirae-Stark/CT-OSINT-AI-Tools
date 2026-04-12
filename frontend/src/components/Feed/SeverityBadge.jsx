export default function SeverityBadge({ severity }) {
  return (
    <span className={`severity-badge severity-${severity}`}>
      {severity}
    </span>
  )
}

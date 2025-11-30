interface SpinnerProps {
  size?: number;
}

export default function Spinner({ size = 32 }: SpinnerProps) {
  return (
    <div
      className="spinner"
      style={{
        width: size,
        height: size,
        border: `${Math.max(2, size / 10)}px solid #333`,
        borderTopColor: '#e9a426',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }}
    />
  );
}

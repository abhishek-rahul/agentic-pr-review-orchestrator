type Props = {
  message: string;
};

export function ReviewStatus({ message }: Props) {
  return <p className="muted">{message}</p>;
}

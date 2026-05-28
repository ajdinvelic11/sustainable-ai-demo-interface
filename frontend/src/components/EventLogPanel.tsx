import type { DemoEvent } from "../types/api";
import EventLog from "./EventLog";

export default function EventLogPanel({ events }: { events: DemoEvent[] }) {
  return <EventLog events={events} />;
}

import type { ChannelEntry } from "@/data/backend";
import { create } from "zustand";

interface ChannelsState {
  byAddress: Record<string, ChannelEntry>;
  setAll: (channels: ChannelEntry[]) => void;
}

// Server data, not a preference: the list comes with the profile and is not persisted.
export const useChannels = create<ChannelsState>()((set) => ({
  byAddress: {},
  setAll: (channels) =>
    set({ byAddress: Object.fromEntries(channels.map((channel) => [channel.address, channel])) }),
}));

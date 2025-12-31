import { create } from 'zustand'

export const useLocationStore = create((set) => ({
  currentLocation: null,
  pickupLocation: null,
  dropoffLocation: null,

  setCurrentLocation: (location) => set({ currentLocation: location }),
  setPickupLocation: (location) => set({ pickupLocation: location }),
  setDropoffLocation: (location) => set({ dropoffLocation: location }),

  clearLocations: () =>
    set({
      pickupLocation: null,
      dropoffLocation: null,
    }),
}))
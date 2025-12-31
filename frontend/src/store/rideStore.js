import { create } from 'zustand'

export const useRideStore = create((set) => ({
  currentRide: null,
  rideHistory: [],
  nearbyDrivers: [],

  setCurrentRide: (ride) => set({ currentRide: ride }),

  updateRideStatus: (status) =>
    set((state) => ({
      currentRide: state.currentRide
        ? { ...state.currentRide, status }
        : null,
    })),

  setNearbyDrivers: (drivers) => set({ nearbyDrivers: drivers }),

  addToHistory: (ride) =>
    set((state) => ({
      rideHistory: [ride, ...state.rideHistory],
    })),

  clearCurrentRide: () => set({ currentRide: null }),
}))
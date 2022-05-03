import { createReducer, on } from '@ngrx/store';
import * as moment from 'moment';
import { LapTime } from 'src/app/models/lap-time';
import { StateContainer } from 'src/app/models/state';

import * as laptimeActions from '../actions/laptime.actions';

export const laptimeFeatureKey = 'laptimes';

export const initialState: StateContainer<LapTime[]> = {
  state: [],
  error: null,
  loading: false,
  lastUpdated: null
};

export const reducer = createReducer(
  initialState,
  on(laptimeActions.loadLaptimes, state => ({
    ...state,
    loading: true
  })),
  on(laptimeActions.loadLaptimesSuccess, (state, action) => ({
    state: action.payload.data,
    error: null,
    loading: false,
    lastUpdated: moment().toDate()
  })),
  on(laptimeActions.loadLaptimesFailure, (state, action) => ({
    ...state,
    error: action.payload.error,
    loading: false,
    lastUpdated: moment().toDate()
  }))
);

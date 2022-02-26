import { Component, Renderer2 } from '@angular/core';
import * as _ from 'lodash';

import { BaseTelemetryDisplayComponent } from '../../base-telemetry-display/base-telemetry-display.component';
import { IracingDataService } from '../../../../services/iracing-data.service';
import { CarImageHelper } from '../../../../_helpers/car-image-helper';

@Component({
  selector: 'app-wheel-display',
  templateUrl: './wheel-display.component.html',
  styleUrls: ['./wheel-display.component.scss']
})

/**
 * Component to show the steering wheel angle
 */
export class WheelDisplayComponent extends BaseTelemetryDisplayComponent {
  driverIndex: number;
  car: string;
  wheelImage: string;

  constructor (
    iracingDataService: IracingDataService,
    private renderer: Renderer2
  ) {
    super(iracingDataService)
  }

  /**
   * Subscribe to iRacing data and start updating the steering wheel angle.
   * The component will attempt to start the stream if it is not
   * already running.
   */
  ngOnInit(): void {
    super.ngOnInit();

    this.iracingDataSubscription = this.iracingDataService.latestData$
      .subscribe(
        data => {
          if (!_.isEmpty(data)) {
            this.driverIndex = data.DriverInfo.DriverCarIdx;

            // Check if the car has changed, update the image accordingly
            let lastCar = this.car;
            this.car = data.DriverInfo.Drivers[this.driverIndex].CarScreenName;
            if ( lastCar !== this.car ) {
              this.wheelImage = CarImageHelper.getImageForCar(this.car);
            }

            this.rotateWheel(data.SteeringWheelAngle)
          }
        }
      );
  }

  /**
   * Rotate the steering wheel graphic by a given number
   * of radians
   *
   * @param radians angle to rotate wheel
   */
  rotateWheel(radians: number) {
    const image = document.getElementById('wheel');

    if (image) {
      this.renderer.setStyle(
        image,
        'transform',
        `rotate(${-radians}rad)`
      );
    }
  }
}

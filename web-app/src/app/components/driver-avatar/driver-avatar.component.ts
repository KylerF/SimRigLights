import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';

import { DriverService } from 'src/app/services/driver.service';
import { Driver } from 'models/driver';

@Component({
  selector: 'app-driver-avatar',
  templateUrl: './driver-avatar.component.html',
  styleUrls: ['./driver-avatar.component.scss']
})

/**
 * Component to display a driver's avatar
 */
export class DriverAvatarComponent implements OnInit, OnChanges {
  // Driver to display the avatar for
  @Input() driver: Driver;

  // Size of the avatar (small, medium, large)
  @Input() size: string;

  avatarURL: string;

  constructor(
    private driverService: DriverService
  ) { }

  ngOnInit(): void {
    this.setAvatarURL();
  }

  /**
   * Update the avatar URL when the driver changes
   */
  ngOnChanges(changes: SimpleChanges) {
    const driverChange = changes.driver;
    const currentProfilePic = driverChange.currentValue?.profilePic;
    const previousProfilePic = driverChange.previousValue?.profilePic;

    if (currentProfilePic && currentProfilePic !== previousProfilePic) {
      this.setAvatarURL();
    }
  }

  /**
   * Set the avatar URL using the driver service
   */
  setAvatarURL() {
    if (this.driver) {
      this.avatarURL = this.driverService.getAvatarURLForDriver(this.driver);
      console.log(this.avatarURL)
    }
  }
}

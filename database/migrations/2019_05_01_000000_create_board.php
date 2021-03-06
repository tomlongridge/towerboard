<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;
use App\Enums\SubscriptionType;
use App\Enums\BoardStatus;

class CreateBoard extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('boards', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->timestamps();
            $table->string('name')->unique();
            $table->string('readable_name');
            $table->unsignedTinyInteger('type')->nullable();
            $table->unsignedBigInteger('created_by'); // FK->users
            $table->unsignedBigInteger('tower_id')->nullable(); // FK->towers
            $table->string('website_url')->nullable();
            $table->string('twitter_handle')->nullable();
            $table->string('facebook_url')->nullable();
            $table->text('info_parking')->nullable();
            $table->text('info_toilets')->nullable();
            $table->text('info_practices')->nullable();
            $table->text('info_services')->nullable();
            $table->string('address')->nullable();
            $table->string('postcode')->nullable();
            $table->float('latitude', 9, 6)->nullable();
            $table->float('longitude', 9, 6)->nullable();
            $table->unsignedTinyInteger('can_post')->default(SubscriptionType::ADMIN);
            $table->unsignedTinyInteger('status')->default(BoardStatus::UNAPPROVED);

            $table->softDeletes();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('boards');
    }
}
